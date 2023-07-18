import inspect
import random
from datetime import timedelta

import alluka
import atsume
import tanjun
import aiohttp

from typing import Annotated, Optional
from tanjun.annotations import Member, Positional, Choices, Str

from .models import *
from .jobs import *
from .utils import *

from util import send_list


# Create your commands here.


@tanjun.as_message_command_group("splatgear2", "sg2")
async def message_group(ctx: tanjun.abc.MessageContext):
    pass


slash_group = tanjun.slash_command_group("splatgear2", "Set alerts for Splatnet2 Gear")

list_group = slash_group.make_sub_group("list", "List available Splatoon 2 gear type, brands, or skills.")


@list_group.as_sub_command("brands", "List available Splatoon 2 brands")
async def list_brands(ctx: atsume.Context):
    await list_properties(ctx, "brand")


@list_group.as_sub_command("skills", "List available Splatoon 2 skills")
async def list_skills(ctx: atsume.Context):
    await list_properties(ctx, "skill")


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@list_group.as_sub_command("gear", "List available Splatoon 2 gear")
async def list_gear_type(ctx: atsume.Context,
                         gear_type: Annotated[Str, "Gear type", Choices(["clothes", "shoes", "head"])]):
    await list_properties(ctx, "gear", gear_type)


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@message_group.as_sub_command("list")
async def list_properties(ctx: atsume.Context, category: Annotated[Str, "Category", Positional()],
                          given_type: Annotated[Optional[Str], "Gear type", Choices(["clothes", "shoes", "head"]), Positional()] = None):
    request_type = category.lower()
    if request_type == "brand" or request_type == "brands":
        async with ctx.get_channel().trigger_typing():
            kinds = [i.name for i in await Brand.objects.all()]
    elif request_type == "gear" or request_type == "gears":
        gear_type = None
        if not given_type:
            await ctx.respond("Error: Unknown gear subtype (must be head, clothes, or shoes)")
            return
        given_type = given_type.lower()
        if given_type == "clothes":
            gear_type = GearEnum.clothes
        elif given_type == "shoes" or gear_type == "shoe":
            gear_type = GearEnum.shoes
        elif given_type == "head" or gear_type == "hat" or gear_type == "hats":
            gear_type = GearEnum.head
        async with ctx.get_channel().trigger_typing():
            kinds = [i.name for i in await Gear.objects.filter(type=gear_type).all()]
    elif request_type == "skill" or request_type == "skills":
        async with ctx.get_channel().trigger_typing():
            kinds = [i.name for i in await Skill.objects.all()]
    else:
        await ctx.respond(f"Error: Unknown type \"{request_type}\"")
        return
    await send_list(ctx.respond, kinds)


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@message_group.as_sub_command("add")
async def add(ctx: atsume.Context, first_filter: Annotated[Optional[Str], "First property to limit to", Positional()] = None,
              second_filter: Annotated[Optional[Str], "Second property to limit to", Positional()] = None,
              third_filter: Annotated[Optional[Str], "Third property to limit to", Positional()] = None):
    brand = None
    gear = None
    skill = None
    args = [first_filter, second_filter, third_filter]
    args = [i for i in args if i]
    kwargs = {"user": ctx.author.id, "last_messaged": datetime.now() - timedelta(days=2)}
    for i in args:
        if not i:
            continue
        new_brand = await Brand.objects.get_or_none(name__iexact=i)
        if new_brand:
            brand = new_brand
            kwargs["brand"] = brand
        new_gear = await Gear.objects.get_or_none(name__iexact=i)
        if new_gear:
            gear = new_gear
            kwargs["gear"] = gear
        new_skill = await Skill.objects.get_or_none(name__iexact=i)
        if new_skill:
            skill = new_skill
            kwargs["skill"] = skill
        if new_brand is None and new_gear is None and new_skill is None:
            await ctx.respond(f"Unknown property \"{i}\"")
            return
    existing_request = GearRequest.objects.filter(**kwargs)
    if existing_request:
        await ctx.respond(f"You already have an alert set for {format_gear_request(gear, brand, skill)}.")
        return
    await GearRequest.objects.create(**kwargs)
    await ctx.respond(f"Added alert for gear with {format_gear_request(gear, brand, skill)}.")


@message_group.as_sub_command("check")
async def check(ctx: atsume.Context, session: alluka.Injected[aiohttp.ClientSession], client: alluka.Injected[tanjun.Client]):
    await check_gear(session, client)
    await ctx.respond("Checked!")
