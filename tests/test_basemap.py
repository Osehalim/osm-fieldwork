#!/usr/bin/python3

# Copyright (c) 2022, 2023 Humanitarian OpenStreetMap Team
#
# This file is part of osm_fieldwork.
#
#     Underpass is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     Underpass is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with osm_fieldwork.  If not, see <https:#www.gnu.org/licenses/>.
#
"""Test functionalty of basemapper.py."""

import logging
import os
import shutil
from io import BytesIO
import json

from osm_fieldwork.basemapper import BaseMapper
from osm_fieldwork.sqlite import DataFile

log = logging.getLogger(__name__)

rootdir = os.path.dirname(os.path.abspath(__file__))
geojson_file_path = f"{rootdir}/testdata/Rollinsville.geojson"
outfile = f"{rootdir}/testdata/rollinsville.mbtiles"
base = "./tiles"


def load_geojson_as_bytesio(geojson_path):
    """Load GeoJSON file and return it as a BytesIO object."""
    with open(geojson_path, 'r') as file:
        geojson_data = json.load(file)
    return BytesIO(json.dumps(geojson_data).encode('utf-8'))


def test_create():
    """Test basemap creation with GeoJSON data passed as BytesIO."""
    hits = 0
    boundary_bytesio = load_geojson_as_bytesio(geojson_file_path)
    basemap = BaseMapper(boundary_bytesio, base, "topo", False)
    tiles = list()
    for level in [8, 9, 10, 11, 12]:
        basemap.getTiles(level)
        tiles += basemap.tiles

    # Adjust the conditions according to the expected outcomes
    if len(tiles) == 5:
        hits += 1

    # Use relevant conditions for x, y values based on your test GeoJSON
    if tiles[0].x == 52 and tiles[1].y == 193 and tiles[2].x == 211:
        hits += 1

    outf = DataFile(outfile, basemap.getFormat())
    outf.writeTiles(tiles, base)

    # Clean up test output
    os.remove(outfile)
    shutil.rmtree(base)

    # Ensure the test hits the expected conditions
    assert hits == 2


if __name__ == "__main__":
    test_create()