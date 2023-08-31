import re
import typing

from aiohttp import ClientSession
from .model_types import ACTIVE_REGEX, Cyclone, WarningType


EVENT = "Tropical Cyclone Statement"
WARNING_REGEX = "CURRENT WATCHES AND WARNINGS:\n- A Tropical Storm (Watch|Warning) is in"


class NOAA:
    BASE_URL = "https://api.weather.gov"

    def __init__(self, session: ClientSession):
        self.session = session

    async def get_zone_by_coords(self, lat: float, long: float):
        r = await self.session.get(f"{self.BASE_URL}/zones", params={"point": f"{lat},{long}"})
        j = (await r.json())["features"]
        zones = [r for r in j if r["properties"]["type"] == "county"]
        return zones[0]["properties"]["id"]

    async def get_current_cyclone_statement(self, zone_id: str) -> list[typing.Any]:
        r = await self.session.get(f"{self.BASE_URL}/alerts/active/zone/{zone_id}")
        reports = (await r.json())["features"]
        cyclones_statements = [r for r in reports if r["properties"]["event"] == EVENT]
        return cyclones_statements

    async def get_current_cyclone_statements_for_zones(self, zone_ids: list[str], current_cyclones: list[Cyclone]) -> dict[Cyclone, dict[WarningType, set[str]]]:
        # For each zone, determine what hurricanes are affecting it and what kind of watch it is under
        # Due to limits with the API, we rely on our own list of current cyclones
        results: dict[Cyclone, dict[WarningType, set[str]]] = {}
        for zone_id in zone_ids:
            statements = await self.get_current_cyclone_statement(zone_id)
            for statement in statements:
                # If there's no headline, it's likely a discontinuation message
                if "NWSheadline" not in statement["properties"]["parameters"]:
                    continue
                headline: str = statement["properties"]["parameters"]["NWSheadline"][0]
                cyclone = None
                for c in current_cyclones:
                    if c.get_full_name() in headline:
                        cyclone = c
                if cyclone is None:
                    print("Didn't match a cyclone", headline)
                    continue
                matches = re.findall(WARNING_REGEX, statement["properties"]["description"])
                assert len(matches) == 1
                warning_type = WarningType(matches[0])
                if not results.get(cyclone):
                    results[cyclone] = {}
                if not results[cyclone].get(warning_type):
                    results[cyclone][warning_type] = set()
                results[cyclone][warning_type].add(zone_id)

        return results




