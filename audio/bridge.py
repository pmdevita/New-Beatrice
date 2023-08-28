import abc
import asyncio
import logging
import struct
import typing

import typing_extensions

logger = logging.getLogger(__name__)

class AbstractCommunicationBridge(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_string(cls, connection_string: str) -> typing_extensions.Self:
        pass

    @abc.abstractmethod
    async def read(self) -> bytes:
        pass

    @abc.abstractmethod
    async def write(self, data: bytes) -> None:
        pass

    @abc.abstractmethod
    async def open(self) -> None:
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        pass

    @abc.abstractmethod
    async def read_loop(self) -> typing.AsyncIterator[bytes]:
        pass

    @property
    @abc.abstractmethod
    def is_alive(self):
        pass


class TCPSocketBridge(AbstractCommunicationBridge):
    def __init__(self, port=12121, reader: typing.Optional[asyncio.StreamReader] = None,
                 writer: typing.Optional[asyncio.StreamWriter] = None) -> None:
        self.port = port
        self.reader: typing.Optional[asyncio.StreamReader] = reader
        self.writer: typing.Optional[asyncio.StreamWriter] = writer

    @classmethod
    def from_string(cls, connection_string: str) -> typing_extensions.Self:
        return cls(int(connection_string))

    async def read(self) -> bytes:
        if not self.reader:
            raise Exception("Attempted to read connection before opening it.")
        size, = struct.unpack('<L', await self.reader.readexactly(4))
        data = await self.reader.readexactly(size)
        return data

    async def write(self, data: bytes) -> None:
        if not self.writer:
            print(self.writer, self.reader)
            raise Exception("Attempted to send data to the manager before the client initialized")
        self.writer.write(struct.pack('<L', len(data)))
        self.writer.write(data)

    async def open(self) -> None:
        if self.writer:
            logger.info("Connection already started")
            return
        self.reader, self.writer = await asyncio.open_connection("127.0.0.1", self.port)

    async def close(self) -> None:
        if self.writer:
            self.writer.close()
        self.writer = None
        self.reader = None

    async def read_loop(self) -> typing.AsyncIterator[bytes]:
        while self.writer:
            yield await self.read()

    def __str__(self):
        return f"{self.__class__.__name__}({self.port})"

    @property
    def is_alive(self):
        return self.writer is not None
