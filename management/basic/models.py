from piccolo.table import Table
from piccolo.columns import BigInt, Integer


class HiCounter(Table):
    user: int = BigInt(primary_key=True)  # Discord User IDs need to be stored as big integers
    count: int = Integer(default=0)
