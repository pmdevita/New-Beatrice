import asyncio
import traceback
import typing
import logging

from hikari import snowflakes

from audio.connection.process_bridge import TCPSocketBridge


if typing.TYPE_CHECKING:
    from audio.voice_connection import VoiceConnection

logger = logging.getLogger(__name__)

MANAGER_PORT = 12121


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
