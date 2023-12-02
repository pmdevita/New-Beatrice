import abc
from abc import abstractmethod
from dataclasses import dataclass

import hikari
import tanjun
from pydantic import BaseModel


@dataclass
class ToolContext:
    channel: hikari.TextableChannel


class OpenAITool(BaseModel):
    @abstractmethod
    async def use_tool(self, ctx: ToolContext, *args, **kwargs) -> str:
        pass
