import array
import typing
import numpy as np
import numpy.typing as np_typing
from audio.libopus._py_opus import ffi, lib # type: ignore
import enum


class OpusApplication(enum.Enum):
    VOIP = lib.OPUS_APPLICATION_VOIP
    AUDIO = lib.OPUS_APPLICATION_AUDIO
    LOWDELAY = lib.OPUS_APPLICATION_RESTRICTED_LOWDELAY


class OpusEncoderSetCTL(enum.Enum):
    COMPLEXITY = lib.OPUS_SET_COMPLEXITY_REQUEST
    BITRATE = lib.OPUS_SET_BITRATE_REQUEST
    BANDWIDTH = lib.OPUS_SET_BANDWIDTH_REQUEST
    INBAND_FEC = lib.OPUS_SET_INBAND_FEC_REQUEST
    PACKET_LOSS_PERC = lib.OPUS_SET_PACKET_LOSS_PERC_REQUEST
    SIGNAL = lib.OPUS_SET_SIGNAL_REQUEST


class OpusEncoderBandwidth(enum.Enum):
    FULL = lib.OPUS_BANDWIDTH_FULLBAND
    MEDIUM = lib.OPUS_BANDWIDTH_MEDIUMBAND
    NARROW = lib.OPUS_BANDWIDTH_NARROWBAND
    SUPERWIDE = lib.OPUS_BANDWIDTH_SUPERWIDEBAND
    WIDE = lib.OPUS_BANDWIDTH_WIDEBAND


class OpusEncodeError(enum.Enum):
    OK = lib.OPUS_OK
    BAD_ARG = lib.OPUS_BAD_ARG
    BUFFER_TOO_SMALL = lib.OPUS_BUFFER_TOO_SMALL
    INTERNAL_ERROR = lib.OPUS_INTERNAL_ERROR
    INVALID_PACKET = lib.OPUS_INVALID_PACKET
    UNIMPLEMENTED = lib.OPUS_UNIMPLEMENTED
    INVALID_STATE = lib.OPUS_INVALID_STATE
    ALLOC_FAIL = lib.OPUS_ALLOC_FAIL


ENCODE_ERRORS = set([item.value for item in OpusEncodeError])


class OpusSignal(enum.Enum):
    AUTO = lib.OPUS_AUTO
    VOICE = lib.OPUS_SIGNAL_VOICE
    MUSIC = lib.OPUS_SIGNAL_MUSIC


class OpusEncoder:
    def __init__(self, sample_rate: typing.Literal[8000, 12000, 16000, 24000, 48000],
                 channels: typing.Literal[1, 2], application: OpusApplication) -> None:
        error_code = ffi.new("int *")
        self._channels = channels
        self._sample_rate = sample_rate
        self._opus_encoder_struct = lib.opus_encoder_create(self._sample_rate, self._channels,
                                                            application.value, error_code)

        self.set_ctl(OpusEncoderSetCTL.BITRATE, 128 * 1024)
        self.set_ctl(OpusEncoderSetCTL.INBAND_FEC, 1)
        self.set_ctl(OpusEncoderSetCTL.PACKET_LOSS_PERC, 15)
        self.set_ctl(OpusEncoderSetCTL.BANDWIDTH, OpusEncoderBandwidth.FULL.value)
        self.set_ctl(OpusEncoderSetCTL.SIGNAL, OpusSignal.AUTO.value)

        self._output_data = ffi.new(f"unsigned char[{3840 * 2}]")
        if error_code[0] != 0:
            raise Exception(f"opus_encoder_create error {error_code[0]}")

    def frame_length_to_size(self, frame_length: int) -> int:
        """

        :param frame_length: Length of the audio frame in milliseconds
        :return: The number of bytes of PCM audio for that frame
        """
        # Number of samples in this frame * channels * size of sample in bits
        return self.frame_length_to_samples(frame_length) * self._channels * int(ffi.sizeof("opus_int16"))

    def frame_length_to_samples(self, frame_length: int) -> int:
        """

        :param frame_length: Length of the audio frame in milliseconds
        :return: The number of samples of PCM audio for that frame
        """
        # Frame length in milliseconds * samples per millisecond
        return frame_length * self._sample_rate // 1000

    def encode_bytes(self, pcm: bytes, frame_size: int) -> bytes:
        # print([int(i) for i in pcm[:8]])
        # assert len(pcm) == 3840
        pre_input_data = ffi.new("int16_t[]", len(pcm) // 2)
        ffi.memmove(pre_input_data, pcm, len(pcm))
        input_data = ffi.cast("int16_t *", pre_input_data)
        # print("my", [int(i) for i in input_data[0:4]])
        output_data = ffi.new(f"char[]", len(pcm))
        packet_length = lib.opus_encode(self._opus_encoder_struct, input_data, frame_size, output_data,
                                        len(pcm))
        assert packet_length >= 0
        print(frame_size, len(pcm))
        print(packet_length)
        if packet_length in ENCODE_ERRORS:
            print(OpusEncodeError(packet_length))

        buffer = ffi.buffer(output_data)
        # return bytes(self._output_data)[0:packet_length]
        return array.array("b", buffer[0:packet_length]).tobytes()

    def encode_numpy(self, pcm: np_typing.NDArray[np.int16], frame_size: int) -> bytes:
        # can we keep this array allocated between encodes?
        # output_data = ffi.new(f"unsigned char[{frame_size}]")
        # test_data = ffi.new(f"short[4]")
        input_data = ffi.cast("int16_t *", pcm.ctypes.data)
        # for i in range(4):
        #     test_data[i] = input_data[i]
        #
        # print("opus data type conversion????", pcm[:4], [int(i) for i in test_data])

        packet_length = lib.opus_encode(self._opus_encoder_struct, input_data, frame_size, self._output_data,
                                        frame_size)
        assert packet_length != -1
        buffer = ffi.buffer(self._output_data)
        result = bytes(buffer)[:packet_length]
        return result

    def set_ctl(self, ctl: OpusEncoderSetCTL, setting: int):
        setting_cdata = ffi.new("int[1]")
        setting_cdata[0] = setting
        print("new ctl", ctl.value, setting)
        lib.opus_encoder_ctl(self._opus_encoder_struct, ctl.value, setting_cdata)

    def close(self):
        lib.opus_encoder_destroy(self._opus_encoder_struct)

    def __del__(self):
        self.close()

    @property
    def channels(self) -> typing.Literal[1, 2]:
        return self._channels


if __name__ == '__main__':
    encoder = OpusEncoder(48000, 2, OpusApplication.VOIP)
    print(encoder.frame_length_to_size(20))
    data = np.zeros(3840, dtype=np.int16)
    encoder.encode_bytes(data.astype(np.int16).tobytes(), encoder.frame_length_to_size(20))
