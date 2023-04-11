#!/usr/bin/python3

# Copyright (c) 2022, 2023 Humanitarian OpenStreetMap Team
#
# This file is part of osm-Fieldwork.
#
#     Osm-Fieldwork is free software: you can redistribute it and/or modify
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

import argparse
import logging
import sys
import os
import pandas as pd
from geojson import Feature, FeatureCollection
import geojson
from osm_fieldwork.xlsforms import xlsforms_path
import yaml


# Instantiate logger
log = logging.getLogger(__name__)


class FilterData(object):
    def __init__(self, filespec=None):
        self.tags = dict()
        if filespec:
            self.parse(filespec)

    def parse(self, filespec):
        # data = pd.read_excel(filespec, sheet_name="Overview - all Tags", usecols=["key", "value"])
        data = pd.read_excel(filespec, sheet_name="choices", usecols=["list name", "name"])
        
        entries = data.to_dict()
        total = len(entries['list name'])
        index = 1
        while index < total:
            key = entries['list name'][index]
            if key == 'model' or str(key) == "nan":
                index += 1
                continue
            if 'name' in entries:
                value = entries['name'][index]
            else:
                value = None
            if value == "<text>" or str(value) == "null":
                index += 1
                continue
            if key not in self.tags:
                self.tags[key] = list()
            self.tags[key].append(value)
            index += 1

        # The yaml config file for the query has a list of columns
        # to keep in addition to this default set.
        path = xlsforms_path.replace("xlsforms", "data_models")
        category = os.path.basename(filespec).replace(".xls", "")
        file = open(f"{path}/{category}.yaml", "r").read()
        data = yaml.load(file, Loader=yaml.Loader)
        self.keep = list()
        self.keep.extend(("name",
                         "name:en",
                         "id",
                         "operator",
                         "addr:street",
                         "addr:housenumber",
                         "osm_id",
                         "title",
                         "tags",
                         "label",
                        ))
        self.keep.extend(data['keep'])

        return self.tags

    def cleanData(self, data):
        tmpfile = data
        if type(data) == str:
            outfile = open(f"new-{data}", "x")
            infile = open(tmpfile, "r")
            indata = geojson.load(infile)
        elif type(data) == bytes:
            indata = eval(data.decode())
        else:
            indata = data
        # these just create noise in the log file
        ignore = (
            "timestamp",
            "version",
            "changeset",
            )
        collection = list()
        for feature in indata['features']:
            properties = dict()
            for key, value in feature['properties'].items():
                if key in self.keep:
                    if key == 'tags':
                        for k, v in value.items():
                            if k[:4] == "name":
                                properties['title'] = value[k]
                                properties['label'] = value[k]
                            else:
                                properties[k] = v
                    else:
                        if key == 'osm_id':
                            properties['id'] = value
                        else:
                            properties[key] = value
                else:
                    if key in self.tags.keys():
                        if key == "name":
                            properties['title'] = self.tags[key]
                            properties['label'] = self.tags[key]
                        if value in self.tags[key]:
                            properties[key] = value
                        else:
                            if value != "yes":
                                log.warning(f"Value {value} not in the data model!")
                            continue
                    else:
                        if key in ignore:
                            continue
                        log.warning(f"Tag {key} not in the data model!")
                        continue
            newfeature = Feature(geometry=feature['geometry'], properties=properties)
            collection.append(newfeature)
        if type(data) == str:
            geojson.dump(FeatureCollection(collection), outfile)
        return FeatureCollection(collection)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert ODK XML instance file to CSV format"
    )
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-i", "--infile", help="The data extract for ODK Collect")
    parser.add_argument("-x", "--xform", help="The XForm for ODK Collect")
    parser.add_argument("-o", "--outfile", default="models.yaml", help="The Yaml file of all tags and values")
    args = parser.parse_args()

    # if verbose, dump to the termina
    if not args.verbose:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        root.addHandler(ch)

    xls = FilterData()
    path = xlsforms_path.replace("xlsforms", "data_models")
    models = FilterData()
    if not args.xform:
        data = models.parse(f"{path}/Impact Areas - Data Models V1.1.xlsx")
    else:
        data = models.parse(args.xform)
    if args.infile:
        cleaned = models.cleanData(args.infile)
    else:
        if os.path.exists(args.outfile):
            os.remove(args.outfile)
        outfile = open(args.outfile, "w")
        current = None
        tab = "    "
        outfile.write("""
        # Do not edit this file, it is generated by the filter_data.py
        # script from the XForm spreadsheet.
        """)
        for key, value in data.items():
            if key != current:
                outfile.write(f"\n{key}:\n")
                for val in value:
                    outfile.write(f"{tab}- {val}\n")

