import alluka
import atsume
import hikari
import tanjun
from aiohttp import web

from typing import Annotated, Optional

from aiohttp.web_fileresponse import FileResponse
from tanjun.annotations import Member, Positional

from atsume.settings import settings
from util.background_tasks import start_background_task

from .models import *


# Create your commands here.

def serve_image(component: atsume.Component):
    async def wrapper(request: web.Request) -> FileResponse:
        start_background_task(yell(component, request))
        return web.FileResponse(settings.SUS_IMAGE_PATH)
    return wrapper


async def yell(component: atsume.Component, request: web.Request) -> None:
    channel = component.client.cache.get_guild_channel(settings.SUS_CHANNEL_ID)
    assert isinstance(channel, hikari.TextableChannel)
    print("IP!!!", request.remote, request.forwarded)
    await channel.send("test")


@atsume.on_open
async def on_open(app: alluka.Injected[web.Application], component: atsume.Component):
    app.add_routes([web.get("/beatrice/image.png", serve_image(component))])
