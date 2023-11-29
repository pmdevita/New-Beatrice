import dataclasses
import typing
from pathlib import Path
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from audio.processing.async_file import AsyncFile


@dataclasses.dataclass
class AudioFile:
    file: str | Path
    volume: float = 1.0
    duck: bool = False
    metadata: typing.Optional[dict] = None
    _id: typing.Optional[int] = None
    guild: typing.Optional[int] = None
    title: typing.Optional[str] = None
    url: typing.Optional[str] = None
    async_file: typing.Optional["AsyncFile"] = None
    cache_name: typing.Optional[str] = None

    def as_dict(self):
        return dataclasses.asdict(self)

    def as_markdown(self):
        return f"[{self.title}]({self.url})"

    def __eq__(self, other):
        if not isinstance(other, AudioFile):
            return False
        if self._id is not None and other._id is not None:
            return self._id == other._id
        if self.url is not None and other.url is not None:
            return self.url == other.url
        if self.title is not None and other.title is not None:
            return self.title == other.title
        return self.file == other.file

    @property
    def id(self):
        return self._id


@dataclasses.dataclass
class AudioChannelConfig:
    name: str
    priority: int = 5


@dataclasses.dataclass
class AudioConfig:
    channels: list[AudioChannelConfig]

