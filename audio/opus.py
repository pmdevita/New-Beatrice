import typing
import numpy as np
import numpy.typing as np_typing
from audio.libopus._py_opus import ffi, lib # type: ignore
import enum


class OpusApplication(enum.Enum):
    VOIP = lib.OPUS_APPLICATION_VOIP
    AUDIO = lib.OPUS_APPLICATION_AUDIO
    LOWDELAY = lib.OPUS_APPLICATION_RESTRICTED_LOWDELAY


class OpusEncoder:
    def __init__(self, sample_rate: typing.Literal[8000, 12000, 16000, 24000, 48000],
                 channels: typing.Literal[1, 2], application: OpusApplication) -> None:
        error_code = ffi.new("int *")
        self._channels = channels
        self._sample_rate = sample_rate
        self._opus_encoder_struct = lib.opus_encoder_create(self._sample_rate, self._channels,
                                                            application.value, error_code)
        if error_code[0] != 0:
            raise Exception(f"opus_encoder_create error {error_code[0]}")

    def encode_bytes(self, pcm: bytes, frame_size: int) -> None:
        pass

    def frame_length_to_size(self, frame_length: int) -> int:
        """

        :param frame_length: Length of the audio frame in milliseconds
        :return:
        """
        return frame_length * self._channels * int(ffi.sizeof("opus_int16")) * int(self._sample_rate / 1000)

    def encode_numpy(self, pcm: np_typing.NDArray[np.int16], frame_size: int) -> None:
        # can we keep this array allocated between encodes?
        output_data = ffi.new(f"unsigned char[{frame_size}]")
        input_data = ffi.cast("opus_int16 *", pcm.ctypes.data)
        packet_length = lib.opus_encode(self._opus_encoder_struct, input_data, frame_size, output_data, frame_size)
        print(packet_length)

    @property
    def channels(self) -> typing.Literal[1, 2]:
        return self._channels


if __name__ == '__main__':
    encoder = OpusEncoder(48000, 2, OpusApplication.VOIP)
    print(encoder.frame_length_to_size(20))
    data = np.zeros(3840, dtype=np.int16)
    encoder.encode_numpy(data, encoder.frame_length_to_size(20))
