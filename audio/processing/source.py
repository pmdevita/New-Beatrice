import asyncio
import io
import logging
import signal
import traceback
import typing
import os
from .async_file import AsyncFile

logger = logging.getLogger(__name__)


class AsyncFFmpegAudio:
    def __init__(self, source: AsyncFile) -> None:
        self._source = source
        self._process: typing.Optional[asyncio.subprocess.Process] = None
        self._buffer = io.BytesIO()
        self.read_task: typing.Optional[asyncio.Task] = None
        self.pause_lock = None
        self.read: typing.Callable[[int], typing.Coroutine[typing.Any, typing.Any, bytes]] = self._start_read

    async def start(self) -> None:
        if self._process:
            return

        args = ["ffmpeg", "-i", "pipe:0", '-loglevel', 'quiet',
                "-filter:a", "loudnorm", "-vn",
                '-f', 's16le', '-ar', '48000', '-ac', '2', "-"]
        self._process = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                             stdin=asyncio.subprocess.PIPE,
                                                             start_new_session=True)
        if self._process is None:
            raise Exception("Oh dear, there's no process, why")
        self.read_task = asyncio.Task(self._read_task())
        logger.info("Start was called on Audio Source")

    async def _read_task(self) -> None:
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
        except BrokenPipeError:
            print("The FFmpeg input pipe was closed while we were still using it")
        except:
            traceback.print_exc()

    async def _start_read(self, size: int = 3840) -> bytes:
        try:
            if self._process is None:
                raise Exception(f"{self.__class__.__name__} tried to read from the FFmpeg process before it started!")
            if len(self._process.stdout._buffer) < size and self._process.returncode is None:
                return bytes(size)
            logger.info("File read started, swapping to read it")
            self.read = self._main_read
            return await self.read()
        except AttributeError as e:
            if self._process is None:
                raise Exception(f"There was an attempt to read a {self.__class__.__name__} without starting it first.")
            else:
                raise e

    async def _main_read(self, size: int = 3840) -> bytes:
        # print("reading next chunk...")
        assert self._process is not None
        assert self._process.stdout is not None
        data = await self._process.stdout.read(size)
        if not data:
            logger.info("Finished reading file, closing")
            await self._process.wait()
            self._process = None
            return bytes(0)
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

    def _send_signal_to_task(self, pid: int, signal: int) -> None:
        try:
            # gpid = os.getpgid(pid)  # WARNING This does not work
            gpid = pid  # But this does!
            # print(f"Sending {signal} to process group {gpid}...")
            # os.kill(gpid, signal)
            os.killpg(pid, signal)
        except:
            traceback.print_exc()
        # print("Done!")

    def _end_process(self) -> None:
        if self._process:
            try:
                # print("Terminating...")
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
