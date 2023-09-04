import traceback
import typing
import numpy as np
from numpy import typing as np_typing

from atsume.settings import settings

from audio.processing.source import AsyncFFmpegAudio
from audio.processing.data import AudioFile

if typing.TYPE_CHECKING:
    from audio.processing.manager import AudioManager


AUDIO_DATA_TYPE = np.dtype("<h")
AUDIO_DATA_TYPE_INFO = np.iinfo(np.int16)


class AudioProcessing:
    def __init__(self, manager: "AudioManager"):
        self.manager = manager
        self.source: typing.Optional[AsyncFFmpegAudio] = None

    async def start(self):
        file = await self.manager.files.open(AudioFile(settings.BASE_DIR / "assets" / "test.webm"))
        # file = await self.manager.files.open(AudioFile(settings.BASE_DIR / "assets" / "beatrice_hi1.opus"))
        self.source = AsyncFFmpegAudio(file)
        await self.source.start()

    async def prepare(self) -> typing.Optional[np_typing.NDArray[np.int16]]:
        assert self.source is not None
        data = await self.source.read()
        if len(data) == 0:
            await self.manager.client.graceful_stop()
        arr = np.frombuffer(data, AUDIO_DATA_TYPE)
        arr = np.clip(arr, a_min=AUDIO_DATA_TYPE_INFO.min, a_max=AUDIO_DATA_TYPE_INFO.max)
        arr = arr.astype(np.int16)
        return arr



