#!/usr/bin/env python

import json
import os
import pathlib
import sys
from datetime import datetime

import requests
import utils


def prepare_link(options: dict, token: str) -> str | None:
    link = f"https://api.openweathermap.org/data/2.5/weather?appid={token}"
    link_fragment = ""

    if options["latitude"] and options["longitude"]:
        # always give priority to lat and long
        link_fragment += f"&lat={options['latitude']}&lon={options['longitude']}"
    else:
        if options["city"]:
            link_fragment += f"&q={options['city']}"
        if not options["country_code"]:
            return
        if options["zip"] and not options["city"]:
            link_fragment += f"&zip={options['zip']}"
        link_fragment += f",{options['country_code']}"

    if options["lang"]:
        # https://openweathermap.org/current#multi
        link_fragment += f"&lang={options['lang']}"

    if options["units"]:
        # standard, metric, imperial
        link_fragment += f"&units={options['units']}"

    return f"{link}{link_fragment}" if link_fragment else None


def assign_glyph(icon_name: str, icons: dict) -> str:
    try:
        return icons[icon_name]
    except KeyError:
        return icons["default"]


def day_night(path_frag: str, time_of_day: str, date_time: datetime) -> pathlib.PosixPath:
    return pathlib.PosixPath(f"{path_frag}/weather-{date_time.strftime('%F')}-{time_of_day}.json")


def cache_and_get(config: dict, fallback: str) -> pathlib.PosixPath:
    now = datetime.now()
    date_path = day_night(config["weather"]["cache_dir"], "day", now)
    if now.hour > 15 or now.hour < 4:
        date_path = day_night(config["weather"]["cache_dir"], "night", now)

    if config["location"]["method"] == "automatic":
        if location_data := utils.auto_locate(config["location"]["cache_dir"]):
            config["weather"] |= location_data
    prepared_link = prepare_link(config["weather"], config["tokens"]["openweather"])

    def callback(metadata: dict) -> dict:
        metadata["weather"][0]["glyph"] = assign_glyph(metadata["weather"][0]["icon"], config["weather"]["icons"])
        return metadata
    if not date_path.is_file() and not utils.fetch_save(prepared_link, str(date_path), callback):
        return fallback
    return json.loads(date_path.read_text())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("No such option!")

    # NOTE: Change these only if you know what you are doing.
    CONFIG_PATH = os.path.expandvars("$XDG_CONFIG_HOME/eww/.config.json")

    FALLBACK = {
        "weather": [
            {
                "main": "NA",
                "glyph": "",
                "icon": "03d"
            }
        ],
        "main": {
            "temp": "NA",
            "feels_like": "NA",
            "temp_min": "NA",
            "temp_max": "NA",
            "pressure": "NA",
            "humidity": "NA"
        },
        "sys": {
            "country": "NA"
        },
        "name": "NA"
    }

    CONFIG = json.loads(pathlib.PosixPath(CONFIG_PATH).read_text())
    CONFIG["weather"]["cache_dir"] = os.path.expandvars(CONFIG["weather"]["cache_dir"])
    CONFIG["location"]["cache_dir"] = os.path.expandvars(CONFIG["location"]["cache_dir"])

    pathlib.PosixPath(CONFIG["weather"]["cache_dir"]).mkdir(parents=True, exist_ok=True)
    pathlib.PosixPath(CONFIG["location"]["cache_dir"]).mkdir(parents=True, exist_ok=True)

    match sys.argv[1]:
        case "fetch":
            _metadata = cache_and_get(CONFIG, FALLBACK)
            print(json.dumps(_metadata))


# vim:filetype=python