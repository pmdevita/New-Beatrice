import asyncio
import logging
import typing
import types
import weakref
from weakref import ref, ReferenceType

import hikari
from hikari import snowflakes, guilds, channels, traits
from hikari.api.voice import VoiceConnection as AbstractVoiceConnection
from audio.utils.background_tasks import BackgroundTasks
from audio.host import VoiceConnection

_VoiceConnectionT = typing.TypeVar("_VoiceConnectionT", bound="AbstractVoiceConnection")

logger = logging.getLogger(__name__)


def _get_vc_proxy(connection: "VoiceConnectionProxy") -> _VoiceConnectionT:
    a = typing.cast(_VoiceConnectionT, connection)
    return a


class VoiceComponent(BackgroundTasks, hikari.impl.VoiceComponentImpl):
    _connections: typing.Dict[snowflakes.Snowflake, VoiceConnection]

    def __init__(self, app: traits.GatewayBotAware):
        super().__init__(app)
        self._proxies: dict[hikari.snowflakes.Snowflake, weakref.WeakSet["VoiceConnectionProxy"]] = {}
        self._closing_connections: set[VoiceConnection] = set()

    async def connect_to(
            self,
            guild: snowflakes.SnowflakeishOr[guilds.PartialGuild],
            channel: snowflakes.SnowflakeishOr[channels.GuildVoiceChannel],
            voice_connection_type: typing.Type[_VoiceConnectionT],
            *,
            deaf: bool = False,
            mute: bool = False,
            timeout: typing.Optional[int] = 5,
            **kwargs: typing.Any,
    ) -> _VoiceConnectionT:
        return await self.connect(guild, channel)

    def _safely_close(self, guild: hikari.snowflakes.Snowflake):
        """If connection has no handles and has nothing in the queue, close it"""
        logger.info("Checking if we can safely close a VoiceConnection...")
        if self.guild_has_active_handles(guild):
            logger.info("Connection still has active handles so we'll keep it alive")
            return
        connection = self._connections.get(guild, None)
        if not connection:
            return
        if connection._has_queue:
            logger.info("Connection still has an active queue so we'll keep it alive")
            return
        logger.info("Connection can be safely closed, closing...")
        self._closing_connections.add(self._connections.pop(guild))
        self.start_background_task(self.disconnect(guild))

    def guild_has_active_handles(self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild]) -> bool:
        guild_id = snowflakes.Snowflake(guild)
        return len(self._proxies[guild_id]) > 0

    async def connect(self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild],
                      channel: snowflakes.SnowflakeishOr[channels.GuildVoiceChannel]) -> VoiceConnection:
        guild_id = snowflakes.Snowflake(guild)
        connection = self.connections.get(guild_id)
        if not connection:
            connection = await super().connect_to(guild_id, channel, VoiceConnection)
        proxy = VoiceConnectionProxy(self, connection)

        if guild_id not in self._proxies:
            proxies: weakref.WeakSet["VoiceConnectionProxy"] = weakref.WeakSet()
            self._proxies[guild_id] = proxies
        else:
            proxies = self._proxies[guild_id]
        proxies.add(proxy)
        return _get_vc_proxy(proxy)

    async def _disconnect_all(self) -> None:
        # We rely on the assumption that _on_connection_close will be called here rather than explicitly
        # emptying self._connections.
        connections = self._connections
        self._connections = {}
        connection_list = connections.values()
        self._closing_connections.update(connection_list)
        await asyncio.gather(*(c.disconnect() for c in connection_list))

    async def disconnect(self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild]) -> None:
        self._check_if_alive()
        guild_id = snowflakes.Snowflake(guild)

        closing_connection = [connection for connection in self._closing_connections if connection.guild_id == guild_id]

        if not closing_connection:
            if guild_id not in self._connections:
                raise hikari.errors.VoiceError("This application doesn't have any active voice connection in this server")

            conn = self._connections.pop(guild_id)
            self._closing_connections.add(conn)
            # We rely on the assumption that _on_connection_close will be called here rather than explicitly
            # to remove the connection from self._connections.
        else:
            conn = closing_connection[0]

        await conn.disconnect()

    async def _on_connection_close(self, connection: hikari.api.voice.VoiceConnection) -> None:
        try:
            if connection.guild_id in self._connections:
                del self._connections[connection.guild_id]
            assert isinstance(connection, VoiceConnection)
            self._closing_connections.remove(connection)

            if not self._connections:
                self._app.event_manager.unsubscribe(hikari.events.VoiceEvent, self._on_voice_event)
                self._voice_listener = False

            # Leave the voice channel explicitly, otherwise we will just appear to
            # not leave properly.
            await self._app.shards[connection.shard_id].update_voice_state(guild=connection.guild_id, channel=None)

            logger.debug(
                "successfully unregistered voice connection %s to guild %s and left voice channel %s",
                connection,
                connection.guild_id,
                connection.channel_id,
            )

        except KeyError:
            logger.warning(
                "ignored closure of phantom unregistered voice connection %s to guild %s. Perhaps this is a bug?",
                connection,
                connection.guild_id,
            )


class VoiceConnectionProxy:
    def __init__(self, component: VoiceComponent, connection: hikari.api.VoiceConnection):
        self.__component = component
        self.__connection = connection

    @classmethod
    def __instancecheck__(cls, instance) -> bool:
        return isinstance(instance, VoiceConnection)

    def __getattr__(self, item):
        return getattr(self.__connection, item)

    def __del__(self):
        self.__component._safely_close(self.__connection.guild_id)
