import typing
from .models import *


def format_gear_request(gear: typing.Optional[Gear], brand: typing.Optional[Brand],
                        skill: typing.Optional[Skill]):
    message = ""
    if gear:
        message += f" type {gear.name}"
    if brand:
        if gear:
            message += ","
        message += f" brand {brand.name}"
    if skill:
        if brand and gear:
            message += ", and"
        elif brand or gear:
            message += " and"
        message += f" skill {skill.name}"
    if message:
        if message[0] == " ":
            message = message[1:]
    return message


def get_image_link(uri):
    return f"https://splatoon2.ink/assets/splatnet{uri}"

