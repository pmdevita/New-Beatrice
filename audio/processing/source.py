import array
import asyncio
import ctypes
import io
import logging
import signal
import traceback
import typing
import os
from .async_file import AsyncFile

logger = logging.getLogger(__name__)


class AsyncFFmpegAudio:
    def __init__(self, source: AsyncFile):
        self._source = source
        self._process: typing.Optional[asyncio.subprocess.Process] = None
        self._buffer = io.BytesIO()
        self.read_task = None
        self.pause_lock = None
        self.read = self._start_read

    async def start(self):
        #  '-loglevel', 'quiet',
        args = ["ffmpeg", "-i", r"E:\pmdevita\Documents\Developer\Python\Discord\Beatrice\assets\test.webm",  # "pipe:0",
                "-filter:a", "loudnorm", "-vn",
                '-f', 's16le', '-ar', '48000', '-ac', '2', "-"]
        self._process = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                             stdin=asyncio.subprocess.PIPE,
                                                             start_new_session=True)
        self.read_task = asyncio.ensure_future(self._read_task())

    async def _read_task(self):
        logger.info(f"Starting pipe from AsyncFile to FFmpeg {self._source}")
        chunk_size = 1024 * 5
        try:
            while True:
                if self.pause_lock:
                    await self.pause_lock.wait()

                chunk = await self._source.read(chunk_size)
                # print(len(chunk))
                if len(chunk) > 0:
                    # print("drain")
                    self._process.stdin.write(chunk)
                    await self._process.stdin.drain()
                else:
                    if self._source.finished_reading():
                        print("Finished reading from AsyncFile")
                        self._process.stdin.write_eof()
                        break
                    # else:
                    #     print("Not finished reading but 0 bytes back?")
        except asyncio.exceptions.CancelledError:
            pass
        except:
            traceback.print_exc()

    async def _start_read(self) -> bytes:
        try:
            if len(self._process.stdout._buffer) < 3840 and self._process.returncode is None:
                return bytes(3840)
            logger.info("File read started, swapping to read it")
            self.read = self._main_read
            return await self.read()
        except AttributeError:
            if self._process is None:
                raise Exception(f"There was an attempt to read a {self.__class__.__name__} without starting it first.")

    async def _main_read(self) -> bytes:
        # print("reading next chunk...")
        data = await self._process.stdout.read(3840)
        # current_time += len(data) / 192 # in milliseconds
        if not data:
            logger.info("Finished reading file, closing")
            await self._process.wait()
            self._process = None
            return bytes(0)
        elif len(data) < 3840:
            data += bytes(3840 - len(data))  # todo: would be better to do within numpy
        return data

    async def pause(self):
        if self.pause_lock:
            if not self.pause_lock.is_set():
                return
        self.pause_lock = asyncio.Event()
        self._send_signal_to_task(self._process.pid, signal.SIGSTOP)

    async def unpause(self):
        if self.pause_lock:
            self.pause_lock.set()
            self.pause_lock = None
        self._send_signal_to_task(self._process.pid, signal.SIGCONT)

    def _send_signal_to_task(self, pid, signal):
        try:
            # gpid = os.getpgid(pid)  # WARNING This does not work
            gpid = pid  # But this does!
            # print(f"Sending {signal} to process group {gpid}...")
            # os.kill(gpid, signal)
            os.killpg(pid, signal)
        except:
            print(traceback.format_exc())
        # print("Done!")

    def _end_process(self):
        if self._process:
            try:
                print("Terminating...")
                # IDK why it needs to be killed but terminating doesn't work. Maybe we need to communicate() and read
                # out all of the data so it can terminate?
                self._process.kill()
            except ProcessLookupError:
                pass
            self._process = None

    async def close(self) -> None:
        self._end_process()
        if self.read_task:
            self.read_task.cancel()
        await self._source.close()

    def __del__(self):
        print("Received delete, terminating...")
        self._end_process()
        if self.read_task:
            self.read_task.cancel()
