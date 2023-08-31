from atsume.db import Model
import ormar

from .api.model_types import CycloneType
from .api.model_types import Cyclone as CycloneDataclass


# Create your models here.


class NOAAZone(Model):
    id = ormar.String(primary_key=True, max_length=8)
    expires = ormar.DateTime(nullable=True, default=None)


class Cyclones(Model):
    pk = ormar.String(primary_key=True, max_length=30)
    year = ormar.SmallInteger()
    name = ormar.String(max_length=25)
    type = ormar.String(max_length=20, choices=list(CycloneType), server_default=CycloneType.TROPICAL_DEPRESSION.value)
    last_update = ormar.DateTime()
    next_update = ormar.DateTime(nullable=True)

    def get_full_name(self):
        return f"{self.type} {self.name}"

    def to_cyclone(self):
        return CycloneDataclass(self.name, CycloneType(self.type))


class Member(Model):
    id = ormar.BigInteger(primary_key=True, autoincrement=False)
    guild_id = ormar.BigInteger()
    ip = ormar.String(max_length=15)
    latitude = ormar.Float()
    longitude = ormar.Float()
    noaa_zone = ormar.ForeignKey(NOAAZone, related_name="members")
    cyclones = ormar.ManyToMany(Cyclones, related_name="members")


class CycloneChannel(Model):
    id = ormar.BigInteger(primary_key=True, autoincrement=False)
    guild_id = ormar.BigInteger()
    cyclone = ormar.ForeignKey(Cyclones, related_name="channels")





