import dataclasses
import enum


class CycloneType(enum.Enum):
    HURRICANE = "Hurricane"
    TROPICAL_DEPRESSION = "Tropical Depression"


@dataclasses.dataclass(eq=True, frozen=True)
class Cyclone:
    name: str
    type: CycloneType

    def get_full_name(self):
        return f"{self.type.value} {self.name}"

    def __str__(self):
        return self.get_full_name()


class WarningType(enum.Enum):
    NONE = "None"
    WATCH = "Watch"
    WARNING = "Warning"


ACTIVE_REGEX = f"({'|'.join([t.value for t in CycloneType])}) (?!Center)(.*?),"
