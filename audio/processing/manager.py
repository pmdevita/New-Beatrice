import asyncio
import logging
import time
import traceback
import typing

import numpy as np
from numpy import typing as np_typing

from audio.processing.async_file import AsyncFileManager
from audio.processing.stats import RollingAverage
from audio.encrypt import encrypt_audio
from audio.opus import OpusEncoder, OpusApplication
from audio.processing.process import AudioProcessing

if typing.TYPE_CHECKING:
    from ..connection.client import VoiceConnectionProcess


logger = logging.getLogger(__name__)


class AudioManager:
    def __init__(self, client: "VoiceConnectionProcess"):
        self.client = client
        self.encoder = OpusEncoder(48000, 2, OpusApplication.VOIP)
        self.frame_size = self.encoder.frame_length_to_size(20)
        self.process = AudioProcessing(self)
        self.files = AsyncFileManager()

    async def start(self):
        try:
            logger.info("Starting audio manager")
            await self.process.start()
            print("starting playback loop")
            count = 0
            send_avg = RollingAverage(250, 0)
            send_avg.add(1)
            loop_start = time.time()
            # await self.client.set_speaking_state(False)
            await self.client.set_speaking_state(True)
            while not self.client.is_stopped:
                pcm = await self.process.prepare()
                packet = await self.prepare_packet(pcm)
                total_offset = (count * 0.02) - (time.time() - loop_start)
                total_wait = round(0.02 + total_offset, 3)
                count += 1
                if count % 250 == 1:
                    await self.client.set_speaking_state(False)
                    await self.client.set_speaking_state(True)
                    print("current total offset", time.time() - loop_start,
                          "waiting for", total_wait, "send avg", send_avg.average())
                if total_wait > 0:
                    try:
                        await asyncio.sleep(total_wait)
                    except asyncio.exceptions.CancelledError:
                        break

                if count > 9000:  # 50 * 60 * 3 minutes
                    count = 1
                    loop_start = time.time()

                start = time.time()
                await self.send_packet(packet)
                send_avg.add(time.time() - start)

        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()

    async def prepare_packet(self, pcm: np_typing.NDArray[np.int16]) -> bytes:
        opus_frame = self.encoder.encode_numpy(pcm, self.frame_size)
        encrypted = await self._encrypt_audio(opus_frame)
        return encrypted

    async def send_packet(self, packet: bytes) -> None:
        await self.client.voice_socket.send(packet)

    async def _encrypt_audio(self, opus_frame: bytes) -> bytes:
        return encrypt_audio(self.client.encrypt_mode, self.client.secret_key,
                             self.client.rtp_header.get_next_header(), opus_frame)