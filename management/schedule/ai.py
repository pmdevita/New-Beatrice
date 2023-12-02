from datetime import datetime

import alluka
import tanjun

from chatgpt.tools import OpenAITool, ToolContext
from atsume.extensions.timer import Timer
from .commands import send_message
from .models import Alarm


class Schedule(OpenAITool):
    time: datetime
    message: str

    class Config:
        name = "scheduler"
        description = "Schedule a message to be sent at a later time in this channel."

    async def use_tool(self, ctx: ToolContext, timer: alluka.Injected[Timer], client: alluka.Client) -> str:
        alarm = await Alarm.objects.create(channel=ctx.channel.id, time=self.time, message=self.message)
        timer.schedule_task(alarm.time, send_message, args=[client, alarm])
        return "Message was scheduled!"



