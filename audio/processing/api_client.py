import logging
import typing
from audio.processing.json import json
from audio.processing.data import AudioFile
from audio.processing.events import Event

if typing.TYPE_CHECKING:
    from audio.processing.manager import AudioManager

logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self, manager: "AudioManager"):
        self.manager = manager

    async def send_event(self, event: Event) -> None:
        event_name = event.__class__.__name__
        data = event.as_dict()
        data["event"] = event_name
        await self.manager.client.manager_connection.write(
            json.dumps(data)
        )

    async def receive_api(self, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.error(f"Audio API message was unable to be decoded! {message}")
            return
        try:
            match data["command"]:
                case "play":
                    await self.manager.process.play(data["channel"])
                case "pause":
                    await self.manager.process.pause(data["channel"])
                case "queue":
                    audio_file = AudioFile(**data["audio"])
                    audio_file.async_file = await self.manager.files.open(audio_file)
                    await self.manager.process.queue(data["channel"], audio_file)
                case "stop":
                    await self.manager.client.graceful_stop()
                case "is_playing":
                    await self.manager.client.manager_connection.write(
                        json.dumps({
                            "command": "is_playing",
                            "id": data["id"],
                            "state": self.manager.process.channels[data["channel"]].is_playing()
                        })
                    )
                case _:
                    logger.error(f"Unknown command \"{data['command']}\"")
        except KeyError as e:
            args = "\", \"".join(e.args)
            logger.error(f"Command \"{data['command']}\" missing properties \"{args}\"")
