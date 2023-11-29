import asyncio
import logging
import time
import traceback
import typing

import numpy as np
from numpy import typing as np_typing

from audio.processing.async_file import AsyncFileManager
from audio.utils.stats import RollingAverage
from audio.data.encrypt import encrypt_audio
from audio.data.opus import OpusEncoder, OpusApplication
from audio.processing.process import AudioPipeline
from audio.data.audio import AudioConfig, AudioChannelConfig
from audio.data.events import Event
from audio.processing.api_client import APIClient
from audio.utils.background_tasks import BackgroundTasks
from ..data import events

if typing.TYPE_CHECKING:
    from ..connection.client import VoiceConnectionProcess

logger = logging.getLogger(__name__)


class AudioManager(BackgroundTasks):
    def __init__(self, client: "VoiceConnectionProcess"):
        super().__init__()
        self.client = client
        self.encoder = OpusEncoder(48000, 2, OpusApplication.AUDIO)
        self.frame_size = self.encoder.frame_length_to_samples(20)
        self.config = AudioConfig([AudioChannelConfig("music", 2), AudioChannelConfig("sfx", 1)])
        self.pipeline = AudioPipeline(self, self.config)
        self.files = AsyncFileManager()
        self.api_client = APIClient(self)

        self.encode_avg = RollingAverage(400, 0)
        self.target_avg = RollingAverage(400, 0)
        self._playback_task: typing.Optional[asyncio.Task] = None
        self._playback_task_running = False
        self._event_subscriptions: dict[
            typing.Type[events.Event],
            list[
                typing.Callable[[events.Event], typing.Coroutine[None, None, None]]
            ]
        ] = {events.AudioChannelEndEvent: [self.check_queues_empty]}

    async def check_queues_empty(self, event: events.Event) -> None:
        assert isinstance(event, events.AudioChannelEndEvent)
        for channel in self.pipeline.channels.values():
            if len(channel._queue) > 0:
                return
        await self.send_event(events.AudioPlaybackFinishedEvent())

    async def playback_task(self):
        try:
            logger.info("Starting AudioManager playback task")
            self._playback_task_running = True
            print("starting playback loop")
            count = 0
            calc_avg = RollingAverage(400, 0)
            target_avg = RollingAverage(400, 0)
            loop_start = time.time()
            # await self.client.set_speaking_state(False)
            await self.client.set_speaking_state(True)
            while not self.client.is_stopped and self._playback_task_running:
                start = time.time()
                pcm = await self.pipeline.read()
                packet = None
                if pcm is not None:
                    packet = await self.prepare_packet(pcm)
                    calc_avg.add(time.time() - start)
                total_offset = (count * 0.02) - (time.time() - loop_start)
                total_wait = round(0.02 + total_offset, 3)
                count += 1
                if count % 250 == 1:
                    print("current total offset", time.time() - loop_start,
                          "avg frame calc time", calc_avg.average(), "send target delta", target_avg.average())
                if total_wait > 0:
                    try:
                        await asyncio.sleep(total_wait)
                    except asyncio.exceptions.CancelledError:
                        break

                if count > 9000:  # 50 * 60 * 3 minutes
                    count = 1
                    loop_start = time.time()

                if packet:
                    target_avg.add(abs((count * 0.02) - (time.time() - loop_start)))
                    await self.send_packet(packet)

        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()
        logger.info("Exiting AudioManager playback task")

    async def prepare_packet(self, pcm: np_typing.NDArray[np.int16]) -> bytes:
        opus_frame = self.encoder.encode_numpy(pcm, self.frame_size)
        encrypted = await self._encrypt_audio(opus_frame)
        return encrypted

    async def send_packet(self, packet: bytes) -> None:
        assert self.client.voice_socket is not None
        await self.client.voice_socket.send(packet)

    async def _encrypt_audio(self, opus_frame: bytes) -> bytes:
        return encrypt_audio(self.client.encrypt_mode, self.client.secret_key,
                             self.client.rtp_header.get_next_header(), opus_frame)

    async def start(self):
        if not self._playback_task:
            self._playback_task_running = True
            self._playback_task = asyncio.Task(self.playback_task())

    async def stop(self):
        if self._playback_task:
            # Attempt to end it gracefully
            self._playback_task_running = False
            try:
                await asyncio.wait_for(self._playback_task, 5)
            except TimeoutError:
                # Just cancel it then
                self._playback_task.cancel()

    async def receive_api(self, message: str) -> None:
        await self.api_client.receive_api(message)

    async def send_event(self, event: Event):
        self.start_background_task(self._dispatch_event(event))

    async def _dispatch_event(self, event: Event):
        self.start_background_task(self.api_client.send_event(event))
        for handle in self._event_subscriptions.get(event.__class__, []):
            self.start_background_task(handle(event))
