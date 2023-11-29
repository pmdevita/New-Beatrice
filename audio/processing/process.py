import asyncio
import numpy as np
from numpy import typing as np_typing

from audio.processing.source import AsyncFFmpegAudio
from audio.data.audio import AudioConfig, AudioFile
from audio.data.events import *
from audio.processing.channel import AudioChannel
from audio.utils.constants import AUDIO_DATA_TYPE_INFO

if typing.TYPE_CHECKING:
    from audio.processing.manager import AudioManager


class AudioPipeline:
    def __init__(self, manager: "AudioManager", config: AudioConfig) -> None:
        self.manager = manager
        self.source: typing.Optional[AsyncFFmpegAudio] = None
        self.config = config
        self.channels: dict[str, AudioChannel] = {channel.name: AudioChannel(self, channel.name)
                                                  for channel in self.config.channels}

    async def queue(self, audio_channel: str, audio_file: AudioFile) -> None:
        await self.channels[audio_channel].queue(audio_file)

    async def play(self, audio_channel: str):
        await self.channels[audio_channel].play()

    async def pause(self, audio_channel: str):
        await self.channels[audio_channel].pause()

    async def _update_play(self, unregister=True):
        playing = False
        for channel in self.channels.values():
            if channel.is_playing():
                playing = True
                await self.manager.register_playback(self, self.voice_channel)
                return
        self._playing = False
        if unregister and not self.stay_in_channel:
            await self.manager.unregister_playback(self)

    async def read(self, size: int = 3840) -> typing.Optional[np_typing.NDArray[np.int16]]:
        # Await reads on all channels
        channel_reads = [channel.read(size) for channel in self.channels.values()]
        await_data = await asyncio.gather(*channel_reads)
        audio_data = [data for data in await_data if data is not None]

        # If we don't have audio data, don't return anything
        if not audio_data:
            return None

        # If we only have one channel, bypass the mix down
        if len(audio_data) == 1:
            return audio_data[0]

        # Mix down the channels
        final = np.stack(audio_data)
        final = np.add(final, 0)
        final = np.clip(final, a_min=AUDIO_DATA_TYPE_INFO.min, a_max=AUDIO_DATA_TYPE_INFO.max)
        final = final.astype(np.int16)  # Todo: Is this necessary
        return final












