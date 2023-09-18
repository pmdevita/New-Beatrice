import typing

import numpy as np
from numpy import typing as np_typing

from audio.processing.automation import VolumeAutomation
from audio.processing.data import AudioFile
from audio.processing.events import AudioChannelEndAutomationEvent, AudioChannelEndEvent, AudioChannelNextEvent, AudioChannelStartEvent
from audio.processing.source import AsyncFFmpegAudio
from audio.processing.constants import AUDIO_DATA_TYPE

if typing.TYPE_CHECKING:
    from audio.processing.process import AudioPipeline


class AudioChannel:
    def __init__(self, pipeline: "AudioPipeline", name: str) -> None:
        self.pipeline = pipeline
        self.name = name
        self._queue: list[AudioFile] = []
        self.source: typing.Optional[AsyncFFmpegAudio] = None
        self.automation: typing.Optional[VolumeAutomation] = None
        self.volume: float = 1
        self._pause = False

    def __repr__(self) -> str:
        return f"AudioChannel({self.source} {'paused' if self._pause else 'play'} {self._queue})"

    def set_volume(self, volume: float, seconds: float = 0) -> None:
        if seconds:
            self.automation = VolumeAutomation(self, self.volume, volume, seconds)
        else:
            self.volume = volume

    async def read(self, size: int = 3840) -> typing.Optional[typing.Optional[np_typing.NDArray[np.int16]]]:
        """Read audio data from the current audio source"""
        if not self.source or self._pause:
            return None

        data = await self.source.read(size)
        should_shift = False
        if not data:
            return None
        if len(data) < size:
            should_shift = True
            data += bytes(size - len(data))
        arr = np.frombuffer(data, dtype=AUDIO_DATA_TYPE)
        if self.automation:
            automation, keep_automating = self.automation.read(size)
            combined = np.stack([arr, automation])
            arr = np.multiply.reduce(combined, 0)
            if not keep_automating:
                self.volume = self.automation.to_target
                self.automation = None
                await self.pipeline.manager.send_event(AudioChannelEndAutomationEvent(self.name))
        elif self.volume != 1:
            arr = (arr * self.volume).astype(np.int16)

        if should_shift:
            await self.shift()

        return arr

    async def shift(self) -> None:
        """
        Pops the first AudioFile in the queue and advances it
        """
        if self.source:
            await self.source.close()
            self.source = None
        if not self._queue:
            return
        await self.pipeline.manager.send_event(AudioChannelEndEvent(self.name, self._queue[0].id))
        self._queue.pop(0)
        if not self._queue:
            return
        await self.pipeline.manager.send_event(AudioChannelNextEvent(self.name, self._queue[0].id))

    def is_playing(self):
        """Is this channel currently playing?"""
        return self.source and not self._pause

    async def stop(self) -> None:
        """Stops playback and clears the queue and pause state"""
        if self.source:
            await self.source.close()
            self.source = None
        self._queue.clear()
        self._pause = False

    async def remove(self, audio_file: AudioFile) -> None:
        if self._queue[0] == audio_file:
            await self.shift()
        else:
            self._queue.remove(audio_file)

    async def play(self) -> None:
        self._pause = False

        # We need AudioFiles queued in order to have something to play, otherwise there's nothing to do
        if not self._queue:
            return

        # If we already have a source, we are probably already playing
        if self.source:
            await self.source.unpause()
            return

        # Open an AsyncFile and open an AsyncFFmpegAudio with it
        audio_file = self._queue[0]
        async_file = audio_file.async_file
        assert async_file is not None
        await async_file.open()
        self.source = AsyncFFmpegAudio(async_file)
        await self.source.start()
        await self.pipeline.manager.send_event(AudioChannelStartEvent(self.name, self._queue[0].id))

    async def pause(self):
        if self.source:
            await self.source.pause()
        self._pause = True

    async def queue(self, audio_file: AudioFile):
        self._queue.append(audio_file)

