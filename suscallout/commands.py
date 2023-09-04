import asyncio
import typing

import aiohttp
import alluka
import atsume
import hikari
from aiohttp import web
from datetime import datetime, timezone

from aiohttp.web_fileresponse import FileResponse

from atsume.settings import settings
from util.background_tasks import start_background_task

from .message import format_message


# Create your commands here.

def serve_image(component: atsume.Component, session: aiohttp.ClientSession) -> \
        typing.Callable[[web.Request], typing.Awaitable[FileResponse]]:
    async def wrapper(request: web.Request) -> FileResponse:
        start_background_task(yell(component, request, session))
        return web.FileResponse(settings.SUS_IMAGE_PATH, headers={"Cache-Control": "no-store"})

    return wrapper


async def serve_test(request: web.Request) -> FileResponse:
    print("oiuashodiufhiaoksdu")
    print(get_ip(request))
    return web.FileResponse(settings.SUS_IMAGE_TEST)


def get_ip(request: web.Request) -> typing.Optional[str]:
    # Get ip address
    ipaddress = request.forwarded[0].get("for", None)
    if not ipaddress:
        ipaddress = request.remote
    return ipaddress


async def get_ip_metadata(session: aiohttp.ClientSession, ipaddress: str) -> dict[str, typing.Any]:
    r = await session.get(f"https://ipinfo.io/{ipaddress}?token={settings.IPINFO_TOKEN}")
    ip_metadata: dict[str, typing.Any] = await r.json()
    return ip_metadata


async def yell(component: atsume.Component, request: web.Request, session: aiohttp.ClientSession) -> None:
    ipaddress = get_ip(request)
    assert ipaddress is not None
    metadata = await get_ip_metadata(session, ipaddress)
    print(ipaddress, metadata)

    if not settings.SUS_ARM:
        return
    # Wait for gif to do animation...
    await asyncio.sleep(2)
    # Assert the bot was loaded
    assert component.client is not None
    assert component.client.cache is not None
    channel = component.client.cache.get_guild_channel(settings.SUS_CHANNEL_ID)
    assert isinstance(channel, hikari.GuildTextChannel)

    assert ipaddress is not None
    if ipaddress == "127.0.0.1":
        print("Who's IP is this request?", request.remote, request.forwarded)
        return
    # Get metadata for the IP


    guild = channel.get_guild()
    assert guild is not None
    member = guild.get_member(int(request.query["id"]))
    assert isinstance(member, hikari.Member)
    now = datetime.now(timezone.utc)
    await channel.send(format_message(member, now, metadata, ipaddress))


@atsume.on_open
async def on_open(app: alluka.Injected[web.Application], component: atsume.Component,
                  session: alluka.Injected[aiohttp.ClientSession]) -> None:
    app.add_routes([web.get("/beatrice/image.png", serve_image(component, session))])
    app.add_routes([web.get("/beatrice/image.mov", serve_test)])
