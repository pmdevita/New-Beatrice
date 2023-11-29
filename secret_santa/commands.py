import hikari
import tanjun
import atsume
import re

from typing import Annotated, Optional
from tanjun.annotations import Member, Positional, Str
from random import choice

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


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@ss_group.as_sub_command("start")
async def start_ss(ctx: atsume.Context, user_string: Annotated[Str, "All members involved", Positional()]):
    user_ids = re.findall("<@(\d*?)>", user_string)
    users = [await ctx.client.rest.fetch_user(int(id)) for id in user_ids]
    print(ctx, user_string)
    print(users, user_ids)
    pairings = shuffle_users(users)

    session = await SecretSantaSession.objects.create(user=ctx.author.id)
    for user, target in pairings:
        await SecretSantaMember.objects.create(session=session, user=user, target=target)

    for user, target in pairings:
        await user.send(f"Hey {user.global_name}! For {ctx.author.global_name}'s secret santa group, "
                        f"your target is {target.mention}! Good luck!")

