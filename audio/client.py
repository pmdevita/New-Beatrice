import asyncio
import json
import logging
import multiprocessing.connection
import traceback
import typing

import aiohttp
import asyncio_dgram

from hikari import snowflakes

from .packet import request_ip, opcode_0_identify, get_ip_response, opcode_3_heartbeat, opcode_1_select
from .encrypt import select_mode

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def process_runtime(channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake, session_id: str,
                    token: str, user_id: snowflakes.Snowflake,
                    pipes: typing.Tuple[
                        multiprocessing.connection.PipeConnection, multiprocessing.connection.PipeConnection]) -> None:
    connection = VoiceConnectionProcess(pipes, channel_id, endpoint, guild_id, session_id, token, user_id)
    asyncio.get_event_loop().run_until_complete(connection.start())


class VoiceConnectionProcess:
    def __init__(self, pipes: typing.Tuple[
        multiprocessing.connection.PipeConnection, multiprocessing.connection.PipeConnection],
                 channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake,
                 session_id: str, token: str, user_id: snowflakes.Snowflake) -> None:
        # Basic information for the connection
        self.manager_pipe, self.process_pipe = pipes
        self.gateway: typing.Optional[aiohttp.ClientWebSocketResponse] = None
        self.voice_socket: typing.Optional[asyncio_dgram.DatagramClient] = None
        self.session = aiohttp.ClientSession()
        self.endpoint = endpoint
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.token = token
        self.session_id = session_id
        self.user_id = user_id

        # Data set later by the Opcode 2 Ready response
        self.ssrc: typing.Optional[int] = None
        self.voice_ip: typing.Optional[str] = None
        self.voice_port: typing.Optional[int] = None
        self.encrypt_mode: typing.Optional[str] = None

        # Data set later by the Opcode 8 Hello response
        self.heartbeat_interval: typing.Optional[float] = None

        # Public IP and Port (discovered once we open the voice UDP socket)
        self.public_ip: typing.Optional[str] = None
        self.public_port: typing.Optional[int] = None

        # Lifecycle-related variables
        self._stop = False
        self._voice_ready = asyncio.Event()
        self._discovery_ready = asyncio.Event()
        self._process_pipe_task: typing.Optional[asyncio.Task] = None
        self._gateway_receive_task: typing.Optional[asyncio.Task] = None
        self._voice_receive_task: typing.Optional[asyncio.Task] = None
        self._heartbeat_task: typing.Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._process_pipe_task = asyncio.Task(self.process_pipe_task())

        # Start the gateway connection
        logger.info(f"Starting the voice gateway connection to {self.endpoint}...")
        self.gateway = await self.session.ws_connect(f"{self.endpoint}?v=4")

        # Send Discord the identify packet
        logger.info("Sending Opcode 0 Identify packet...")
        await self.gateway.send_str(
            opcode_0_identify(str(self.guild_id), str(self.user_id), self.session_id, self.token))

        # Start the socket listening task
        self._gateway_receive_task = asyncio.Task(self.gateway_receive_task())
        logger.info("Waiting for the voice receive packet...")
        await self._voice_ready.wait()

        # Establish the voice UDP connection
        logger.info(f"Connecting to the voice UDP socket on {self.voice_ip}:{self.voice_port}")
        self.voice_socket = await asyncio_dgram.connect((self.voice_ip, self.voice_port))

        # Request our public IP and port through the voice UDP connection
        logger.info(f"Requesting public IP and port to the voice UDP socket...")
        assert self.ssrc is not None
        await self.voice_socket.send(request_ip(self.ssrc))
        logger.info("Waiting to discover public IP and port...")
        data = await self.voice_socket.recv()
        self.public_ip, self.public_port = get_ip_response(data[0])
        logger.info(f"Discovered public IP and port {self.public_ip}:{self.public_port}!")

        # Start the voice receive task
        self._voice_receive_task = asyncio.Task(self.voice_receive_task())

        # Send the select packet
        logger.info(f"Sending Opcode 1 Select packet with mode {self.encrypt_mode}...")
        assert self.public_ip is not None and self.public_port is not None and self.encrypt_mode is not None
        await self.gateway.send_str(opcode_1_select(self.public_ip, self.public_port, self.encrypt_mode))

        await asyncio.sleep(10)
        print("ending...")
        await self.stop()
        print('end')

    async def stop(self) -> None:
        self._stop = True
        if self._process_pipe_task:
            self._process_pipe_task.cancel()
            self._process_pipe_task = None
        if self._gateway_receive_task:
            self._gateway_receive_task.cancel()
            self._gateway_receive_task = None
        if self._voice_receive_task:
            self._voice_receive_task.cancel()
            self._voice_receive_task = None
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self.gateway:
            await self.gateway.close()
            self.gateway = None
        if self.voice_socket:
            self.voice_socket.close()
            self.voice_socket = None

    async def process_pipe_task(self) -> None:
        try:
            read_event = asyncio.Event()
            asyncio.get_event_loop().add_reader(self.process_pipe.fileno(), read_event.set)
            while not self._stop:
                if not self.process_pipe.poll():
                    await read_event.wait()
                read_event.clear()
                if not self.process_pipe.poll():
                    continue

                data = self.process_pipe.recv()
                if data == "stop":
                    await self.stop()
        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()

    async def gateway_receive_task(self) -> None:
        try:
            while not self._stop and self.gateway:
                data = await self.gateway.receive(30)
                match data.type:
                    case aiohttp.WSMsgType.TEXT:
                        await self.receive_opcode(json.loads(data.data))
                    case aiohttp.WSMsgType.ERROR:
                        print("Received WS error")
                        await self.stop()
                    case aiohttp.WSMsgType.CLOSE:
                        print("WS closed")
                        await self.stop()
                    case _:
                        raise Exception(f"Unhandled WSMsgType {data.type}")
        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()

    async def voice_receive_task(self) -> None:
        try:
            while not self._stop and self.voice_socket:
                data = await self.voice_socket.recv()
                # print(data)
            logger.info("Exiting voice receive task...")
        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()

    async def heartbeat_task(self) -> None:
        try:
            while not self._stop and self.gateway and self.heartbeat_interval is not None:
                logger.info("Sending Opcode 3 Heartbeat...")
                await self.gateway.send_str(opcode_3_heartbeat(598209))
                await asyncio.sleep(self.heartbeat_interval)
        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()

    async def receive_opcode(self, data: dict) -> None:
        opcode_data: dict = data["d"]
        print(data)
        match data["op"]:
            # Ready Opcode
            case 2:
                logger.info("Receive Opcode 2 Voice Ready!")
                self.ssrc = opcode_data["ssrc"]
                self.voice_ip = opcode_data["ip"]
                self.voice_port = opcode_data["port"]
                self.encrypt_mode = select_mode(opcode_data["modes"])
                self._voice_ready.set()
            # Hello Opcode
            case 8:
                logger.info("Receive Opcode 8 Hello!")
                self.heartbeat_interval = opcode_data["heartbeat_interval"] / 1000
                if not self._heartbeat_task:
                    self._heartbeat_task = asyncio.Task(self.heartbeat_task())