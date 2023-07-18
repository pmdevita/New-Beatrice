from datetime import timedelta, timezone, datetime

import atsume
import alluka
import aiohttp
import random

import hikari
import tanjun

from .models import *
from .utils import *


@atsume.on_open
async def loader(session: alluka.Injected[aiohttp.ClientSession]):
    async with session.get("https://splatoon2.ink/data/locale/en.json") as response:
        data = await response.json()
        for gear_type in GearEnum:
            await synchronize_gear_list(data["gear"][gear_type.value], Gear, gear_type=gear_type.value)
        # Synchronize brands
        await synchronize_gear_list(data["brands"], Brand)
        # Synchronize skills
        await synchronize_gear_list(data["skills"], Skill)


async def synchronize_gear_list(gear_list, model: typing.Type[Model], gear_type=None):
    gears = {int(gear): gear_list[gear]["name"] for gear in gear_list}
    for gear_row in await model.objects.all():
        # If we are using types, make sure this has a matching one first
        if gear_type:
            if gear_type != gear_row.type.value:
                continue
        # Remove from our dictionary if there is a match, otherwise delete it
        if gears.get(gear_row.id, None) == gear_row.name:
            gears.pop(gear_row.id)
        else:
            await gear_row.delete()
    kwargs = {}
    if gear_type:
        kwargs["type"] = gear_type
        kwargs["pid"] = "temp"
    for gear in gears:
        await model.objects.create(id=gear, name=gears[gear], **kwargs)


@atsume.as_time_schedule(minutes=random.randrange(0, 59))
async def check_gear(session: alluka.Injected[aiohttp.ClientSession], client: alluka.Injected[tanjun.Client]):
    async with session.get("https://splatoon2.ink/data/merchandises.json") as response:
        data = await response.json()
    for merch in data["merchandises"]:
        given_gear_type = merch["gear"]["kind"]
        if given_gear_type == "head":
            gear_type = GearEnum.head
        elif given_gear_type == "clothes":
            gear_type = GearEnum.clothes
        else:
            gear_type = GearEnum.shoes
        gear = await Gear.objects.get(id=int(merch["gear"]["id"]), type=gear_type)
        brand = await Brand.objects.get(id=int(merch["gear"]["brand"]["id"]))
        skill = await Skill.objects.get(id=int(merch["skill"]["id"]))

        gear_image = get_image_link(merch["gear"]["image"])
        skill_image = get_image_link(merch["skill"]["image"])
        brand_image = get_image_link(merch["gear"]["brand"]["image"])

        rows = await GearRequest.objects.filter(
            ((GearRequest.gear.pid == gear.pid) | (GearRequest.gear.pid.isnull(True))) &
            ((GearRequest.brand.id == brand.id) | (GearRequest.brand.id.isnull(True))) &
            ((GearRequest.skill.id == skill.id) | (GearRequest.skill.id.isnull(True))) &
            (GearRequest.last_messaged <= (datetime.now(tz=timezone.utc) - timedelta(hours=12)))
        ).select_related(["gear", "brand", "skill"]).all()

        for request in rows:
            user = client.cache.get_user(request.user)
            channel = await user.fetch_dm_channel()
            message = f"An item with {format_gear_request(gear, brand, skill)} " \
                      f"is available on the SplatNet store! (Your request was for an item with " \
                      f"{format_gear_request(request.gear, request.brand, request.skill)})"
            embed1 = hikari.Embed(title="Splatgear Alert!", description=message)
            embed1.set_image(gear_image)
            embed1.set_thumbnail(brand_image)

            embed2 = hikari.Embed()
            embed2.set_thumbnail(skill_image)
            embeds = [embed1, embed2]

            # Kind of a mess but decides where images should go based on request options
            # thumbnail_priority = []
            # if request.skill:
            #     thumbnail_priority.append(skill_image)
            # if request.brand:
            #     thumbnail_priority.append(brand_image)
            # if request.gear:
            #     embed1.set_image(gear_image)
            #     thumbnail = thumbnail_priority.pop(0)
            #     if thumbnail:
            #         embed1.set_thumbnail(thumbnail)
            #     if thumbnail_priority:
            #         embed2 = nextcord.Embed()
            #         embed2.set_thumbnail(thumbnail_priority[0])
            # else:
            #     thumbnail = thumbnail_priority.pop(0)
            #     if thumbnail:
            #         embed1.set_thumbnail(thumbnail)
            #     if thumbnail_priority:
            #         embed1.set_image(thumbnail_priority[0])
            # embeds = [embed1]
            # if embed2:
            #     embeds.append(embed2)

            await channel.send(embeds=embeds)
            request.last_messaged = datetime.now(timezone.utc)
            await request.update()
