import re
import typing

import bs4
from aiohttp import ClientSession
from bs4 import BeautifulSoup
import time

from hurricane.api.model_types import CycloneType, Cyclone, ACTIVE_REGEX

THRESHOLD = 60 * 60
FEED_URL = "https://www.nhc.noaa.gov/index-at.xml"
ACTIVE_HURRICANE_TITLE = "Atlantic Tropical Weather Outlook"
CONE_IMAGE_REGEX = "https://www\\.nhc\\.noaa\\.gov/storm_graphics/(.*?)/(.*?)_5day_cone_with_line_and_wind_sm2.png"


class NHC:
    def __init__(self, session: ClientSession):
        self.session = session
        self.feed: typing.Optional[BeautifulSoup] = None
        self.entries: list[BeautifulSoup] = []
        self.last_checked = 0

    async def check_feed(self):
        if time.time() < self.last_checked + THRESHOLD:
            return

        self.last_checked = time.time()
        r = await self.session.get(FEED_URL)
        self.feed = BeautifulSoup(await r.text(), "lxml-xml")
        self.entries = []
        for child in self.feed.channel.children:
            if isinstance(child, bs4.NavigableString):
                continue
            if child.name != "item":
                continue
            self.entries.append(child)

    async def get_active_hurricanes(self) -> list[Cyclone]:
        await self.check_feed()
        entry = [i for i in self.entries if i.title.text == ACTIVE_HURRICANE_TITLE]
        if entry:
            entry = entry[0]
        else:
            return []
        text: str = entry.description.text
        start = text.index("Active Systems:<br/>")
        end = text.index("<br/>\n<br/>\n", start)
        text = text[start: end]
        text = text.replace("<br/>\n", "")
        matches = re.findall(ACTIVE_REGEX, text)
        names = []
        for match in matches:
            names.append(Cyclone(match[1], CycloneType(match[0])))
        print(names)
        return names

    async def get_storm_cone_image(self, cyclone: Cyclone) -> typing.Optional[str]:
        await self.check_feed()
        entry = [i for i in self.entries if i.title.text == f"{cyclone.type.value} {cyclone.name} Graphics"]
        if entry:
            entry = entry[0]
        else:
            return None
        text: str = entry.description.text
        matches = re.findall(CONE_IMAGE_REGEX, text)
        if len(matches) == 0:
            return None
        return f"https://www.nhc.noaa.gov/storm_graphics/{matches[0][0]}/refresh/{matches[0][1]}_5day_cone_no_line_and_wind+png/"

