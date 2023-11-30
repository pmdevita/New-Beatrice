import alluka
import hikari
import tanjun
import atsume
import re

from typing import Annotated, Optional, List

from hikari import Member
from tanjun.annotations import Member, Positional, Str
from random import choice

from tanjun.dependencies import async_cache

from secret_santa.models import *


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command_group("secretsanta")
async def ss_group(ctx: atsume.Context):
    ...


def shuffle_users(users: list[hikari.User]) -> list[tuple[hikari.User, hikari.User]]:
    users_without = users[:]
    user_pairings = []
    for user in users:
        possible_users = [u for u in users_without if u != user]
        target = choice(possible_users)
        users_without.remove(target)
        user_pairings.append((user, target))
    return user_pairings


async def parse_members(argument: str, /, ctx: alluka.Injected[tanjun.abc.Context]) -> list[Member]:
    snowflakes = tanjun.conversion.search_user_ids(argument)
    members = []
    guild_id = ctx.guild_id
    if guild_id is None:
        raise ValueError("Can't get members if not in guild")
    for m in snowflakes:
        if ctx.cache:
            try:
                obj = ctx.cache.get_member(guild_id, m)
                if obj:
                    members.append(obj)
                    continue
            except async_cache.EntryNotFound:
                raise ValueError("Couldn't find member in this guild")

            except async_cache.CacheMissError:
                pass

        try:
            obj = await ctx.rest.fetch_member(guild_id, m)
            if obj:
                members.append(obj)
        except hikari.NotFoundError:
            raise ValueError("Couldn't find member in this guild")
    return members


@tanjun.with_greedy_argument("users", converters=parse_members)
@tanjun.parsing.with_parser
@ss_group.as_sub_command("start")
async def start_ss(ctx: atsume.Context, users: list[hikari.Member]):
    pairings = shuffle_users([m.user for m in users])

    session = await SecretSantaSession.objects.create(user=ctx.author.id)
    for user, target in pairings:
        await SecretSantaMember.objects.create(session=session, user=user, target=target)

    for user, target in pairings:
        await user.send(f"Hey {user.global_name}! For {ctx.author.global_name}'s secret santa group, "
                        f"you are buying a gift for {target.mention}! Good luck!")
