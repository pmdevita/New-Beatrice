from atsume.db import Model
import ormar


# Create your models here.

class SecretSantaSession(Model):
    id = ormar.Integer(autoincrement=True, primary_key=True)
    user = ormar.BigInteger(nullable=False)


class SecretSantaMember(Model):
    id = ormar.Integer(autoincrement=True, primary_key=True)
    session = ormar.ForeignKey(SecretSantaSession, related_name="members", ondelete=ormar.ReferentialAction.CASCADE)
    user = ormar.BigInteger(nullable=False)
    target = ormar.BigInteger(nullable=False)

