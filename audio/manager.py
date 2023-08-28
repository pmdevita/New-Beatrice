import asyncio
import concurrent.futures
import logging
import multiprocessing
import multiprocessing.connection
import struct
import traceback
import typing

import hikari.errors
from hikari import snowflakes
from hikari.events import voice_events
from typing_extensions import Self

from hikari.api import VoiceConnection as AbstractVoiceConnection, VoiceComponent

from audio.client import process_runtime
from audio.bridge import TCPSocketBridge, AbstractCommunicationBridge

logger = logging.getLogger(__name__)

_pool = concurrent.futures.ProcessPoolExecutor()
_job_end_tasks: set[asyncio.Task] = set()

MANAGER_PORT = 12121


def start_background_task(coro: typing.Awaitable[typing.Any]) -> None:
    async def log_exceptions() -> None:
        try:
            await coro
        except Exception as e:
            traceback.print_exc()

    task = asyncio.create_task(log_exceptions())
    _job_end_tasks.add(task)
    task.add_done_callback(_job_end_tasks.discard)


class VoiceManager:
    def __init__(self) -> None:
        self.server: typing.Optional[asyncio.Server] = None
        self.connections: typing.Dict[snowflakes.Snowflake, "VoiceConnection"] = {}

    async def start_server(self) -> None:
        if not self.server:
            logger.info("Starting bridge server")
            self.server = await asyncio.start_server(self.client_connected, host="127.0.0.1", port=MANAGER_PORT)

    async def add_listener(self, guild_id: snowflakes.Snowflake, connection: "VoiceConnection") -> None:
        self.connections[guild_id] = connection

    async def client_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            connection = TCPSocketBridge(reader=reader, writer=writer)
            print("client connected", reader, writer)
            guild = await connection.read()
            guild_id = int(guild.decode())
            logger.info(f"Client process for guild {guild_id} connected")
            await self.connections[snowflakes.Snowflake(guild_id)]._set_connection(connection)
        except:
            traceback.print_exc()

    async def remove_listener(self, guild_id):
        del self.connections[guild_id]
        if len(self.connections) == 0 and self.server:
            logger.info("Last voice client closed, dropping bridge server")
            self.server.close()
            self.server = None


manager = VoiceManager()


class VoiceConnection(AbstractVoiceConnection):
    def __init__(self, pipes: typing.Tuple[
        multiprocessing.connection.PipeConnection, multiprocessing.connection.PipeConnection],
                 job: asyncio.Future, on_close: typing.Callable[["VoiceConnection"], typing.Awaitable[None]],
                 channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake,
                 owner: VoiceComponent, session_id: str, shard_id: int, token: str,
                 user_id: snowflakes.Snowflake) -> None:
        self.manager_pipe, self.process_pipe = pipes
        self.job = job
        self.close_callback = on_close

        self._is_alive = True
        self._channel_id = channel_id
        self._endpoint = endpoint
        self._guild_id = guild_id
        self._owner = owner
        self._shard_id = shard_id

        self.client_connection: typing.Optional[AbstractCommunicationBridge] = None
        self._client_task: typing.Optional[asyncio.Task] = None

    async def job_end(self) -> None:
        """Here we wait for the coprocess to end. This should be the main way of exiting the connection."""
        try:
            await self.job
        except (KeyboardInterrupt, asyncio.CancelledError):
            if not self.job.cancelled():
                self.job.cancel()
        self._is_alive = False
        if self.client_connection:
            await self.client_connection.close()
            await manager.remove_listener(self._guild_id)
        try:
            await self.close_callback(self)
        except hikari.errors.ComponentStateConflictError:   # Might happen during shutdown
            pass
        if self._client_task:
            self._client_task.cancel()

    @classmethod
    async def initialize(cls, channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake,
                         on_close: typing.Callable[["VoiceConnection"], typing.Awaitable[None]], owner: VoiceComponent,
                         session_id: str, shard_id: int, token: str, user_id: snowflakes.Snowflake,
                         **kwargs: typing.Any) -> Self:
        loop = asyncio.get_running_loop()
        pipes: typing.Tuple[
            multiprocessing.connection.PipeConnection, multiprocessing.connection.PipeConnection] = multiprocessing.Pipe(
            True)
        await manager.start_server()
        job: asyncio.Future = loop.run_in_executor(_pool, process_runtime, channel_id, endpoint, guild_id, session_id,
                                                   token, user_id, pipes, MANAGER_PORT)
        connection = cls(pipes, job, on_close, channel_id, endpoint, guild_id, owner, session_id, shard_id,
                         token, user_id)
        await manager.add_listener(guild_id, connection)
        start_background_task(connection.job_end())
        return connection

    async def _set_connection(self, connection: AbstractCommunicationBridge) -> None:
        self.client_connection = connection

    async def client_task(self) -> None:
        try:
            while self._is_alive and self.client_connection:
                data = await self.client_connection.read()
                print("received on bot side", data.decode())
        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()

    @property
    def channel_id(self) -> snowflakes.Snowflake:
        return self._channel_id

    @property
    def guild_id(self) -> snowflakes.Snowflake:
        return self._guild_id

    @property
    def is_alive(self) -> bool:
        return self._is_alive

    @property
    def shard_id(self) -> int:
        return self._shard_id

    @property
    def owner(self) -> VoiceComponent:
        return self._owner

    async def disconnect(self) -> None:
        if self.client_connection:
            await self.client_connection.write("stop".encode())

    async def join(self) -> None:
        pass

    async def notify(self, event: voice_events.VoiceEvent) -> None:
        pass
