import dataclasses
import typing


@dataclasses.dataclass(eq=True, frozen=True)
class Event:
    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(eq=True, frozen=True)
class AudioChannelNextEvent(Event):
    """An AudioChannel has advanced its queue to the next AudioFile"""
    channel_name: str
    audio_file_id: typing.Optional[int]


@dataclasses.dataclass(eq=True, frozen=True)
class AudioChannelEndEvent(Event):
    """An AudioChannel has ended playback for an AudioFile"""
    channel_name: str
    audio_file_id: int


@dataclasses.dataclass(eq=True, frozen=True)
class AudioChannelEndAutomationEvent(Event):
    """An AudioChannel has ended automation"""
    channel_name: str


@dataclasses.dataclass(eq=True, frozen=True)
class AudioChannelStartEvent(Event):
    """An AudioChannel has started playback of an AudioFile"""
    channel_name: str
    audio_file_id: int


@dataclasses.dataclass(eq=True, frozen=True)
class AudioPlaybackFinishedEvent(Event):
    """Playback of all queued AudioFiles in all AudioChannels has completed.

    Useful to signal termination of the voice client.
    """
    pass


events: dict[str, typing.Type[Event]] = {
    "AudioChannelNextEvent": AudioChannelNextEvent,
    "AudioChannelEndEvent": AudioChannelEndEvent,
    "AudioChannelEndAutomationEvent": AudioChannelEndAutomationEvent,
    "AudioChannelStartEvent": AudioChannelStartEvent,
    "AudioPlaybackFinishedEvent": AudioPlaybackFinishedEvent
}
