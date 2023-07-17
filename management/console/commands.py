import asyncio
import typing

import alluka
import atsume
import tanjun
import aioconsole


from util import start_background_task
from .models import *

# Create your commands here.


class Variables:
    cancel = False
    command_task: typing.Optional[asyncio.Task] = None


def register(name: str):
    async def wrapper(func):
        await func()

    commands[name] = wrapper
    return wrapper


async def get_command(client: tanjun.Client):
    while not Variables.cancel:
        command = await aioconsole.ainput()
        start_background_task(parse_command(client, command))


async def parse_command(client: tanjun.Client, command):
    if command == "":
        return
    command_tokens = command.split(" ")
    i = 0
    while i < len(command_tokens):
        while command_tokens[i][0] == "\"" and command_tokens[i][-1] != "\"" and i < len(command_tokens) - 1:
            command_tokens[i] = command_tokens[i] + " " + command_tokens[i + 1]
            command_tokens.pop(i + 1)
        if command_tokens[i][0] == "\"" and command_tokens[i][-1] == "\"":
            command_tokens[i] = command_tokens[i][1: -1]
        i += 1
    func = commands.get(command_tokens[0], None)
    if func:
        await func(client, *command_tokens[1:])


@atsume.on_open
async def loader(client: alluka.Injected[tanjun.Client]) -> None:
    Variables.command_task = asyncio.create_task(get_command(client))


@atsume.on_close
async def unloader() -> None:
    Variables.cancel = True
    if Variables.command_task:
        Variables.command_task.cancel()


async def cogs(client: tanjun.Client):
    print(client.components)


async def guilds(client: tanjun.Client):
    print([client.cache.get_guild(g) for g in client.cache.get_guilds_view()])


commands = {
    "cogs": cogs,
    "guilds": guilds
}

