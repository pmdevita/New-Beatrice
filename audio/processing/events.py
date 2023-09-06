import dataclasses
import typing

from .data import AudioFile

@dataclasses.dataclass
class Event:
    pass


@dataclasses.dataclass
class AudioChannelNextEvent(Event):
    """An AudioChannel has advanced its queue to the next AudioFile"""
    channel_name: str
    audio_file: typing.Optional[AudioFile]


@dataclasses.dataclass
class AudioChannelEndEvent(Event):
    """An AudioChannel has ended playback for an AudioFile"""
    channel_name: str
    audio_file: AudioFile


@dataclasses.dataclass
class AudioChannelEndAutomationEvent(Event):
    """An AudioChannel has ended automation"""
    channel_name: str


@dataclasses.dataclass
class AudioChannelPlayEvent(Event):
    """An AudioChannel has started playback of an AudioFile"""
    channel_name: str
    audio_file: AudioFile


