import re


def upgrade_image_url(url: str):
    match = re.match("https://www\.nhc\.noaa\.gov/storm_graphics/(.*?)/(.*?)_5day_cone_with_line_and_wind_sm2.png", url)
    return f"https://www.nhc.noaa.gov/storm_graphics/{match.group(1)}/refresh/{match.group(2)}_5day_cone_no_line_and_wind+png/"


if __name__ == '__main__':
    print(
        upgrade_image_url("https://www.nhc.noaa.gov/storm_graphics/AT10/AL102023_5day_cone_with_line_and_wind_sm2.png"))
