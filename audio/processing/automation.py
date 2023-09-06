import numpy as np
import numpy.typing as np_typing
from audio.processing.np_types import AUDIO_DATA_TYPE

SAMPLES_PER_SECOND = 48000


class VolumeAutomation:
    def __init__(self, channel, from_target: float, to_target: float, seconds: float) -> None:
        self.channel = channel
        self.from_target = from_target
        self.to_target = to_target
        self.samples = seconds * SAMPLES_PER_SECOND
        self.current = 0

    def is_automating(self) -> bool:
        return self.current < self.samples - 1

    def read(self, size: int) -> tuple[np_typing.NDArray[np.int16], bool]:
        diff = self.to_target - self.from_target
        arr: np_typing.NDArray[np.int16] = np.fromfunction(  # type: ignore
            lambda x: diff * ((x + self.current) / self.samples) + self.from_target, shape=(size,),
            dtype=AUDIO_DATA_TYPE)
        self.current += size
        if not self.is_automating():
            self.channel.automation_complete()
        return arr, self.is_automating()
