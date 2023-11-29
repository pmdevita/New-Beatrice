import hikari
import tanjun
import atsume

from atsume.settings import settings

from audio.host import VoiceConnection
from audio.data.audio import AudioFile


# Create your commands here.


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("vc")
async def vc_test(ctx: atsume.Context) -> None:
    guild = ctx.get_guild()
    voice = ctx.voice
    if not guild or not voice:
        return
    assert ctx.member is not None
    voice_state = guild.get_voice_state(ctx.member)
    if not voice_state:
        return
    voice_channel_id = voice_state.channel_id
    assert voice_channel_id is not None
    voice_channel = guild.get_channel(voice_channel_id)
    assert isinstance(voice_channel, hikari.GuildVoiceChannel)
    connection = await voice.connect_to(guild, voice_channel, VoiceConnection)
    await connection.queue_and_wait("music", AudioFile(str(settings.BASE_PATH / "assets" / "dougcongrats.ogg")))
    print("Queue and wait completed!")
    # await connection.queue("music", AudioFile(str(settings.BASE_PATH / "assets" / "test.webm")))
    # await connection.play("music")
    # await asyncio.sleep(5)
    # start = time.time()
    # state = await connection.is_playing("music")
    # result = time.time() - start
    # print("isplaying", state, result)


# @tanjun.annotations.with_annotated_args(follow_wrapped=True)
# @tanjun.as_message_command("dc")
# async def dc_test(ctx: atsume.Context) -> None:
#     global connection
#     if connection:
#         await connection.disconnect()




