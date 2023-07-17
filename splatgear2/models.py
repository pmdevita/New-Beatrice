import typing
from datetime import datetime
from enum import Enum

from atsume.db import Model
import ormar
from ormar import pre_save

# Create your models here.


class Brand(Model):
    id = ormar.Integer(primary_key=True, autoincrement=False)
    name = ormar.String(max_length=30)


class Skill(Model):
    id = ormar.Integer(primary_key=True, autoincrement=False)
    name = ormar.String(max_length=30)


class GearEnum(Enum):
    head = "head"
    shoes = "shoes"
    clothes = "clothes"


class Gear(Model):
    pid: str = ormar.String(name="_pid", max_length=18, primary_key=True)
    id: int = ormar.Integer()
    type: GearEnum = ormar.Enum(enum_class=GearEnum)
    name: str = ormar.String(max_length=30)


@pre_save(Gear)
async def pre_save_album(sender: typing.Type[Gear], instance: Gear, **kwargs):
    instance.pid = f"{instance.type.value}_{instance.id}"


class GearRequest(Model):
    id: int = ormar.Integer(primary_key=True)
    user: int = ormar.BigInteger()
    # TODO: Add delete constraints when they hit stable
    gear: typing.Optional[Gear] = ormar.ForeignKey(Gear, name="gear_id", related_name="requests", nullable=True, ondelete=ormar.ReferentialAction.CASCADE)
    brand: typing.Optional[Brand] = ormar.ForeignKey(Brand, name="brand_id", related_name="requests", nullable=True, ondelete=ormar.ReferentialAction.CASCADE)
    skill: typing.Optional[Skill] = ormar.ForeignKey(Skill, name="skill_id", related_name="requests", nullable=True, ondelete=ormar.ReferentialAction.CASCADE)
    last_messaged: datetime = ormar.DateTime()




