import asyncio
import gc
import logging
import sys
import typing

import alluka
import atsume
import tanjun
import aioconsole

from atsume.component.manager import manager
from atsume.bot import load_component


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
    print("Components loaded:")
    for i in client.components:
        print(f"- {i.name}")


async def guilds(client: tanjun.Client):
    print("Guilds active in:")
    for i in client.cache.get_guilds_view():
        g = client.cache.get_guild(i)
        print(f"- \"{g.name}\" ({g.id})")


async def unload(client: tanjun.Client, component_name: str):
    component = client.get_component_by_name(component_name)
    client.remove_component_by_name(component_name)
    component_config = manager.get_config_by_name(component_name)
    keys = []
    for i in sys.modules.keys():
        if i.startswith(component_config.module_path):
            logging.info(f"reloading module {i}")
            keys.append(i)
    manager.unload_component(component_config)
    del component_config
    del component
    gc.collect()
    # print(gc.get_objects())
    print(f"{component_name} unloaded.")


async def load(client: tanjun.Client, component_name: str):
    component_config = manager.load_component(component_name=component_name)
    load_component(client, component_config)
    print(f"{component_name} loaded.")


async def reload(client: tanjun.Client, component_name: str):
    await unload(client, component_name)
    await load(client, component_name)


commands = {
    "cogs": cogs,
    "components": cogs,
    "apps": cogs,
    "guilds": guilds,
    "unload": unload,
    "load": load,
    "reload": reload,
}

