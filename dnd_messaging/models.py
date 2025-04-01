import hikari
from atsume.db import Model
import ormar
from random import randrange
from math import floor

# Create your models here.


def roll_stat() -> int:
    rolls = [randrange(1, 7) for i in range(4)]
    rolls.sort()
    return sum(rolls[1:])


def ability_score_to_modifier(score: int) -> int:
    return floor((score - 10) / 2)


class DNDStatsChannel(Model):
    guild = ormar.BigInteger(primary_key=True)
    channel = ormar.BigInteger()


class DNDStats(Model):
    user = ormar.BigInteger(primary_key=True)
    charisma = ormar.Integer(minimum=1, maximum=20)
    intelligence = ormar.Integer(minimum=1, maximum=20)
    wisdom = ormar.Integer(minimum=1, maximum=20)
    deception = ormar.Integer(minimum=1, maximum=20)
    humor = ormar.Integer(minimum=1, maximum=20)

    @classmethod
    def create(cls, user: hikari.User):
        return cls(user.id, roll_stat(), roll_stat(), roll_stat(), roll_stat(), roll_stat())
