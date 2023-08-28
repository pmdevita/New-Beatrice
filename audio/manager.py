import asyncio
import concurrent.futures
import multiprocessing
import multiprocessing.connection
import traceback
import typing

from hikari import snowflakes
from hikari.events import voice_events
from typing_extensions import Self

from hikari.api import VoiceConnection as AbstractVoiceConnection, VoiceComponent

from audio.client import process_runtime

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
    def __init__(self):
        self.server: typing.Optional[asyncio.Server] = None
        self.connections: typing.Dict[snowflakes.Snowflake, "VoiceConnection"] = {}

    async def add_listener(self, guild_id: snowflakes.Snowflake, connection: "VoiceConnection"):
        if not self.server:
            self.server = await asyncio.start_server(self.client_connected, host="127.0.0.1", port=MANAGER_PORT)
        self.connections[guild_id] = connection

    async def client_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        print("client connected", reader, writer)

    async def remove_listener(self, guild_id):
        del self.connections[guild_id]
        if len(self.connections) == 0 and self.server:
            self.server.close()


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
        self.endpoint = endpoint
        self._guild_id = guild_id
        self._owner = owner
        self._shard_id = shard_id

        self.reader: typing.Optional[asyncio.StreamReader] = None
        self.writer: typing.Optional[asyncio.StreamWriter] = None

    async def job_end(self) -> None:
        """Here we wait for the coprocess to end. This should be the main way of exiting the connection."""
        await self.job
        self._is_alive = False
        await self.close_callback(self)

    @classmethod
    async def initialize(cls, channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake,
                         on_close: typing.Callable[["VoiceConnection"], typing.Awaitable[None]], owner: VoiceComponent,
                         session_id: str, shard_id: int, token: str, user_id: snowflakes.Snowflake,
                         **kwargs: typing.Any) -> Self:
        loop = asyncio.get_running_loop()
        pipes: typing.Tuple[
            multiprocessing.connection.PipeConnection, multiprocessing.connection.PipeConnection] = multiprocessing.Pipe(
            True)
        job: asyncio.Future = loop.run_in_executor(_pool, process_runtime, channel_id, endpoint, guild_id, session_id,
                                                   token, user_id, pipes)
        connection = cls(pipes, job, on_close, channel_id, endpoint, guild_id, owner, session_id, shard_id,
                         token, user_id)
        start_background_task(connection.job_end())
        return connection

    async def _set_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

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
        pass

    async def join(self) -> None:
        pass

    async def notify(self, event: voice_events.VoiceEvent) -> None:
        pass
