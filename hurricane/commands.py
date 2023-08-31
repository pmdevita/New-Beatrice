import json
import typing

import aiohttp
import alluka
import hikari
import tanjun
import atsume
from pathlib import Path
from aiohttp import web
from datetime import datetime

from atsume.settings import settings

from typing import Annotated, Optional
from tanjun.annotations import Member, Positional, Float, Str

from .api.noaa import NOAA
from .api.nhc import NHC
from .api.model_types import WarningType

from .models import NOAAZone, Cyclones, CycloneChannel
from .models import Member as MemberModel
from .jobs import *


# Create your commands here.


@atsume.on_open
async def on_open(client: alluka.Injected[tanjun.abc.Client], session: alluka.Injected[aiohttp.ClientSession],
                  app: alluka.Injected[web.Application]):
    noaa = NOAA(session)
    client.set_type_dependency(NOAA, noaa)
    client.set_type_dependency(NHC, NHC(session))
    app.add_routes([web.get("/beatrice/hurricane", signup_page),
                    web.post("/beatrice/hurricane", signup(noaa))])


async def signup_page(request: web.Request):
    page_path = Path(__file__).parent / "web" / "index.html"
    with open(page_path) as f:
        page = f.read()
    page = page.replace("BASE_URL", settings.WEB_SERVER_URL_BASE)
    return web.Response(body=page, content_type="text/html")


def get_ip(request: web.Request) -> typing.Optional[str]:
    # Get ip address
    ipaddress = request.remote
    if request.forwarded:
        ipaddress = request.forwarded[0].get("for", None)
    return ipaddress


def signup(noaa: NOAA):
    async def wrapper(request: web.Request):
        j = json.loads(await request.content.read())
        print(j)
        m = await MemberModel.objects.get_or_none(id=j["member"])
        zone_id = await noaa.get_zone_by_coords(j["lat"], j["long"])
        noaa_zone, exists = await NOAAZone.objects.get_or_create(id=zone_id)

        if not m:
            m = await MemberModel.objects.create(id=j["member"], guild_id=j["guild"], ip=get_ip(request),
                                             latitude=j["lat"], longitude=j["long"], noaa_zone=noaa_zone)
        else:
            m.guild_id = j["guild"]
            m.ip = get_ip(request)
            m.latitude = j["lat"]
            m.longitude = j["long"]
            m.noaa_zone = noaa_zone
            await m.update()
        return web.Response(status=201)
    return wrapper

slash_group = tanjun.slash_command_group("weather", "Set alerts for hurricane weather")


@tanjun.as_message_command_group("weather", "w")
def weather_group(ctx: atsume.Context) -> None:
    pass


def get_year():
    return datetime.now().year


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@weather_group.as_sub_command("add")
@slash_group.as_sub_command("add", "Register for hurricane alerts", default_to_ephemeral=True)
async def add_user(ctx: atsume.Context):
    await ctx.respond(f"Open this link to register {settings.WEB_SERVER_URL_BASE}beatrice/hurricane?member={ctx.member.id}&guild={ctx.get_guild().id}")


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@weather_group.as_sub_command("check")
async def check_cmd(ctx: atsume.Context, noaa: alluka.Injected[NOAA], nhc: alluka.Injected[NHC]):
    await check_cyclones(noaa, nhc)


async def check_cyclones(noaa: alluka.Injected[NOAA], nhc: alluka.Injected[NHC]):
    """Check for new cyclones and if found, send first alerts, and start watching them"""
    year = datetime.now().year
    cyclones = await nhc.get_active_hurricanes()
    for cyclone in cyclones:
        cyclone_model, was_created = await Cyclones.objects.get_or_create(pk=f"{year}_{cyclone.name}", _defaults={
            "year": year,
            "name": cyclone.name,
            "type": cyclone.type.value,
            "last_update": datetime.now(),
            "next_update": datetime.now()
        })
        if cyclone_model.type != cyclone.type.value:
            cyclone_model.type = cyclone.type.value
            await cyclone_model.update()


@atsume.as_time_schedule(seconds=0)
async def send_alerts(component: atsume.Component, noaa: alluka.Injected[NOAA], nhc: alluka.Injected[NHC],
                      client: alluka.Injected[tanjun.Client]):
    assert component.client is not None
    assert component.client.cache is not None
    await check_cyclones(noaa, nhc)
    for guild_id in component.guilds:
        guild = component.client.cache.get_guild(guild_id)
        if guild is None:
            continue
        await check_guild_cyclones(client, guild, noaa, nhc)


# Ormar currently doesn't support SELECT DISTINCT
async def get_guild_zones(guild: hikari.Guild) -> list[str]:
    members = await MemberModel.objects.filter(guild_id=guild.id).all()
    zone_ids = set([member.noaa_zone.id for member in members])
    return list(zone_ids)


async def check_guild_cyclones(client: tanjun.Client, guild: hikari.Guild, noaa: NOAA, nhc: NHC):
    """Check the status of all cyclones for a guild"""
    assert client.cache is not None
    now = datetime.now()
    zone_ids = await get_guild_zones(guild)
    cyclone_models = await Cyclones.objects.filter(next_update__isnull=False, next_update__lte=now, year=get_year()).all()
    cyclones = [c.to_cyclone() for c in cyclone_models]
    status = await noaa.get_current_cyclone_statements_for_zones(zone_ids, cyclones)
    if len(status) == 0:
        # Currently no storms affecting this guild
        return

    members: list[MemberModel] = await MemberModel.objects.filter(guild_id=guild.id).select_related(["cyclones",
                                                                                                    "noaa_zone"]).all()
    # There is at least one storm affecting this guild, send a warning
    for cyclone in status.keys():
        cyclone_model = await Cyclones.objects.get(name=cyclone.name, type=cyclone.type.value)
        cyclone_channel, is_first = await get_cyclone_channel(client, guild, cyclone_model)
        # Figure out what users are in which zone
        warning_users = [m for m in members if m.noaa_zone.id in status[cyclone].get(WarningType.WARNING, [])]
        watch_users = [m for m in members if m.noaa_zone.id in status[cyclone].get(WarningType.WATCH, [])]
        # Figure out which users have not been alerted before
        all_users = []
        all_users.extend(warning_users)
        all_users.extend(watch_users)
        new_members = []
        for m in all_users:
            if cyclone_model not in m.cyclones:
                new_members.append(m)
        new_member_mentions = member_model_to_member(client, guild, new_members)
        message = f"{'ALERT: New Storm Approaching!' if is_first else 'UPDATE:'}\n"

        if new_member_mentions:
            message += f"{' '.join([m.mention for m in new_member_mentions if m])}\n\n"

        if watch_users:
            message += f"Watch:\n{member_list(member_model_to_member(client, guild, watch_users))}\n\n"

        if warning_users:
            message += f"Warning:\n{member_list(member_model_to_member(client, guild, warning_users))}\n\n"

        message += f"{await nhc.get_storm_cone_image(cyclone)}"

        await cyclone_channel.send(message)


def member_model_to_member(client: tanjun.Client, guild: hikari.Guild, member_models: list[MemberModel]) \
        -> list[hikari.Member]:
    assert client.cache is not None
    members: list[hikari.Member] = []
    for m in member_models:
        member = client.cache.get_member(guild, m.id)
        if member:
            members.append(member)
    return members


def member_list(members: list[hikari.Member]) -> str:
    string = ""
    for member in members:
        string += f"- {member.display_name}\n"
    return string


async def get_cyclone_channel(client: tanjun.Client, guild: hikari.Guild, cyclone_model: Cyclones) \
        -> typing.Tuple[hikari.GuildTextChannel, bool]:
    """Returns a GuildTextChannel and a boolean of whether this is the first alert for this guild and cyclone"""
    channel_model = await CycloneChannel.objects.get_or_none(guild_id=guild.id, cyclone=cyclone_model)
    assert client.cache is not None
    if channel_model is None:
        new_channel = await guild.create_text_channel(
            cyclone_model.get_full_name(),
            topic=f"Discussing {cyclone_model.get_full_name()}"
        )
        await CycloneChannel.objects.create(id=new_channel.id, guild_id=guild.id, cyclone=cyclone_model)
        return new_channel, True
    else:
        c = client.cache.get_guild_channel(channel_model.id)
        assert isinstance(c, hikari.GuildTextChannel)
        return c, False
