import asyncio
import json
import logging
import multiprocessing.connection
import os
import struct
import traceback
import typing

import aiohttp
import asyncio_dgram

from hikari import snowflakes

from atsume.bot import initialize_atsume


from audio.connection.discord_packet import request_ip, opcode_0_identify, get_ip_response, opcode_3_heartbeat, \
    opcode_1_select, RTPHeader, opcode_5_speaking
from audio.connection.process_bridge import AbstractCommunicationBridge, TCPSocketBridge
from audio.encrypt import select_mode
from audio.processing.manager import AudioManager
from audio.utils.background_tasks import BackgroundTasks

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def process_runtime(channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake, session_id: str,
                    token: str, user_id: snowflakes.Snowflake,
                    manager_port: int) -> None:
    try:
        settings_module = os.environ["ATSUME_SETTINGS_MODULE"]
        initialize_atsume(settings_module)
        connection = VoiceConnectionProcess(channel_id, endpoint, guild_id, session_id, token, user_id, manager_port)
        asyncio.get_event_loop().run_until_complete(connection.start())
    except KeyboardInterrupt:
        pass
    except:
        traceback.print_exc()


class VoiceConnectionProcess(BackgroundTasks):
    def __init__(self, channel_id: snowflakes.Snowflake, endpoint: str, guild_id: snowflakes.Snowflake, session_id: str,
                 token: str, user_id: snowflakes.Snowflake, manager_port: int, *args, **kwargs) -> None:
        super().__init__()
        # Basic information for the connection
        self.manager_connection: AbstractCommunicationBridge = TCPSocketBridge(port=manager_port)
        self.gateway: typing.Optional[aiohttp.ClientWebSocketResponse] = None
        self.voice_socket: typing.Optional[asyncio_dgram.DatagramClient] = None
        self.session = aiohttp.ClientSession()
        self.endpoint = endpoint
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.token = token
        self.session_id = session_id
        self.user_id = user_id
        self.manager_port = manager_port
        self.audio = AudioManager(self)

        # Data set later by the Opcode 2 Ready response
        self.ssrc: typing.Optional[int] = None
        self.voice_ip: typing.Optional[str] = None
        self.voice_port: typing.Optional[int] = None
        self.encrypt_mode: typing.Optional[str] = None
        self.rtp_header: typing.Optional[RTPHeader] = None

        # Data set later by the Opcode 4 Session Description response
        self.secret_key: typing.Optional[bytes] = None

        # Data set later by the Opcode 8 Hello response
        self.heartbeat_interval: typing.Optional[float] = None

        # Public IP and Port (discovered once we open the voice UDP socket)
        self.public_ip: typing.Optional[str] = None
        self.public_port: typing.Optional[int] = None

        # Lifecycle-related variables
        self._stop = False
        self._stop_event = asyncio.Event()
        self._voice_ready = asyncio.Event()
        self._audio_ready = asyncio.Event()
        self._discovery_ready = asyncio.Event()
        self._process_pipe_task: typing.Optional[asyncio.Task] = None
        self._manager_pipe_task: typing.Optional[asyncio.Task] = None
        self._gateway_receive_task: typing.Optional[asyncio.Task] = None
        self._voice_receive_task: typing.Optional[asyncio.Task] = None
        self._heartbeat_task: typing.Optional[asyncio.Task] = None
        self._audio_task: typing.Optional[asyncio.Task] = None

    async def start(self) -> None:
        # Connect back to the main bot
        await self.manager_connection.open()
        await self.manager_connection.write(str(self.guild_id).encode())
        self._manager_pipe_task = asyncio.Task(self.manager_pipe_task())

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

        await self.manager_connection.write("done!".encode())

        # Once we receive Opcode 4 with the secret key we can continue
        await self._audio_ready.wait()
        self._audio_task = asyncio.Task(self.audio.playback_task())

        # Wait until we receive the stop event, which only fires after clean up completes
        await self._stop_event.wait()
        logger.info(f"Terminating event loop for {self.guild_id}")

    async def stop(self) -> None:
        try:
            logger.info(f"Stopping audio client for guild {self.guild_id}...")
            self._stop = True
            if self._audio_task:
                self._audio_task.cancel()
                self._audio_task = None
            if self._manager_pipe_task:
                self._manager_pipe_task.cancel()
                self._manager_pipe_task = None
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
            if self.session:
                if not self.session.closed:
                    # I don't know why this error happens, but it complains if we don't end the session
                    try:
                        await self.session.close()
                    except asyncio.CancelledError:
                        pass
            if self.gateway:
                # If this isn't closed by now, don't even bother because it'll just hang the whole thing
                # await self.gateway.close(code=4000, message=b"")
                if not self.gateway.closed:
                    logger.warning(f"Audio gateway for {self.guild_id} wasn't closed gracefully!")
                self.gateway = None
            if self.voice_socket:
                self.voice_socket.close()
                self.voice_socket = None
            # Close the infinite wait to fully exit the asyncio loop
            self._stop_event.set()
        except:
            traceback.print_exc()

    async def graceful_stop(self):
        await self.audio.stop()
        if self.gateway:
            logger.info("Trying to cancel the gateway websocket...")
            await self.gateway.close(code=4000, message=b"")
            logger.info("Sent close request!")
        else:
            await self.stop()

    async def set_speaking_state(self, state: bool):
        print("pls speak", opcode_5_speaking(self.ssrc, microphone=state))
        await self.gateway.send_str(opcode_5_speaking(self.ssrc, microphone=state))

    @property
    def is_stopped(self):
        return self._stop

    async def manager_pipe_task(self) -> None:
        try:
            while not self._stop and self.manager_connection.is_alive:
                data = await self.manager_connection.read()
                string = data.decode()
                print("got data", string)
                if string == "stop":
                    # The gateway just hates if you don't handle its closing and listen for its events,
                    # so we request to close it if possible instead.
                    # This then hangs this task I'm pretty sure ugh
                    await self.graceful_stop()
                else:
                    self.start_background_task(self.audio.receive_api(string))
        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()

    async def process_pipe_task(self) -> None:
        # Todo: remove this over the new bridge stuff
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
                    case aiohttp.WSMsgType.CLOSING:
                        logger.info("Gateway is closing...")
                    case aiohttp.WSMsgType.CLOSED:
                        logger.info("Gateway is closed, ending client process")
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
                self.rtp_header = RTPHeader(self.ssrc)
                self._voice_ready.set()
            # Session Description Opcode
            case 4:
                self.encrypt_mode = opcode_data["mode"]
                self.secret_key = bytes(opcode_data["secret_key"])
                self._audio_ready.set()
            # Hello Opcode
            case 8:
                logger.info("Receive Opcode 8 Hello!")
                self.heartbeat_interval = opcode_data["heartbeat_interval"] / 1000
                if not self._heartbeat_task:
                    self._heartbeat_task = asyncio.Task(self.heartbeat_task())
