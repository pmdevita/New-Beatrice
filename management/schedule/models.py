from atsume.db import Model
import ormar
from datetime import datetime

# Create your models here.


class Alarm(Model):
    id: int = ormar.Integer(primary_key=True, autoincrement=True)
    channel: int = ormar.BigInteger()
    time: datetime = ormar.DateTime()
    message: str = ormar.Text()


