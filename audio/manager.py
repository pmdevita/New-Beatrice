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

from audio.connection.client import VoiceConnectionProcess, process_runtime
from audio.connection.process_bridge import TCPSocketBridge, AbstractCommunicationBridge
from audio.processing.data import AudioFile
from audio.utils.background_tasks import BackgroundTasks
from audio.processing.json import json
from audio.processing import events

logger = logging.getLogger(__name__)

_job_end_tasks: set[asyncio.Task] = set()

MANAGER_PORT = 12121
multiprocessing.set_start_method("spawn")


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


class VoiceConnection(BackgroundTasks, AbstractVoiceConnection):
    _POOL = concurrent.futures.ProcessPoolExecutor()

    def __init__(self, job: asyncio.Future, on_close: typing.Callable[["VoiceConnection"], typing.Awaitable[None]],
                 channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake, owner: VoiceComponent,
                 session_id: str, shard_id: int, token: str, user_id: snowflakes.Snowflake) -> None:
        super().__init__()
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
        self._client_connected = asyncio.Event()

        self._id = 1
        self._callbacks: dict[int, list[asyncio.Future]] = {}
        self._events: dict[events.Event, list[asyncio.Future]] = {}
        self._loop = asyncio.get_running_loop()

    def _get_id(self):
        id = self._id
        self._id += 1
        return id

    async def job_end(self) -> None:
        """Here we wait for the coprocess to end. This should be the main way of exiting the connection."""
        try:
            await self.job
        except concurrent.futures.process.BrokenProcessPool:
            traceback.print_exc()
            logger.info("Repairing process pool...")
            self.__class__._POOL.shutdown()
            self.__class__._POOL = concurrent.futures.ProcessPoolExecutor()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            if not self.job.cancelled():
                self.job.cancel()
        self._is_alive = False
        if self.client_connection:
            await self.client_connection.close()
            await manager.remove_listener(self._guild_id)
            self.client_connection = None
        try:
            await self.close_callback(self)
        except hikari.errors.ComponentStateConflictError:  # Might happen during shutdown
            pass
        if self._client_task:
            self._client_task.cancel()

    @classmethod
    async def initialize(cls, channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake,
                         on_close: typing.Callable[["VoiceConnection"], typing.Awaitable[None]], owner: VoiceComponent,
                         session_id: str, shard_id: int, token: str, user_id: snowflakes.Snowflake,
                         **kwargs: typing.Any) -> Self:
        loop = asyncio.get_running_loop()
        await manager.start_server()

        job: asyncio.Future = loop.run_in_executor(cls._POOL, process_runtime, channel_id, endpoint, guild_id, session_id,
                                                   token, user_id, MANAGER_PORT)
        connection = cls(job, on_close, channel_id, endpoint, guild_id, owner, session_id, shard_id,
                         token, user_id)
        await manager.add_listener(guild_id, connection)
        connection.start_background_task(connection.job_end())
        return connection

    async def _set_connection(self, connection: AbstractCommunicationBridge) -> None:
        self.client_connection = connection
        self._client_task = asyncio.Task(self.client_task())
        self._client_connected.set()

    async def client_task(self) -> None:
        try:
            while self._is_alive and self.client_connection:
                data = await self.client_connection.read()
                print("bot got", data)
                j = json.loads(data.decode())
                if j.get("event", None):
                    await self.fire_event_callback(j)
                elif j.get("id", None):
                    await self.fire_id_event(j)
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

    async def _send_message(self, data: dict):
        if not self.client_connection:
            await self._client_connected.wait()
        await self.client_connection.write(json.dumps(data))

    async def await_callback(self, id: int) -> typing.Any:
        fut = self._loop.create_future()
        if self._callbacks.get(id, None):
            self._callbacks[id].append(fut)
        else:
            self._callbacks[id] = [fut]
        return await fut

    def await_event(self, event: events.Event) -> asyncio.Future[events.Event]:
        fut = self._loop.create_future()
        if self._events.get(event, None):
            self._events[event].append(fut)
        else:
            self._events[event] = [fut]
        return fut

    async def fire_id_event(self, message: typing.Any) -> None:
        id = message["id"]
        try:
            futures = self._callbacks.pop(id)
        except KeyError:
            return
        for fut in futures:
            fut.set_result(message)

    async def fire_event_callback(self, message: typing.Any) -> None:
        event_name = message["event"]
        message.pop("event")
        event = events.events[event_name](**message)  # type: ignore
        try:
            futures = self._events.pop(event)
        except KeyError:
            return
        for fut in futures:
            fut.set_result(event)

    async def notify(self, event: voice_events.VoiceEvent) -> None:
        pass

    async def play(self, channel: str):
        await self._send_message({"command": "play", "channel": channel})

    async def pause(self, channel: str):
        await self._send_message({"command": "pause", "channel": channel})

    async def queue(self, channel: str, file: AudioFile):
        await self._send_message({"command": "queue", "channel": channel, "audio": file.as_dict()})

    async def is_playing(self, channel: str):
        id = self._get_id()
        await self._send_message({"command": "is_playing", "channel": channel, "id": id})
        result = await self.await_callback(id)
        return result["state"]

    async def queue_and_wait(self, channel: str, file: AudioFile):
        id = self._get_id()
        data = file.as_dict()
        data["_id"] = id
        event = self.await_event(events.AudioChannelStartEvent(channel, id))
        await self._send_message({"command": "queue", "channel": channel, "audio": data})
        await self.play(channel)
        res = await event
        print("queued and waited complete!", res)




