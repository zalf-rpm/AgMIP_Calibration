#!/usr/bin/python
# -*- coding: latin1

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/. */

# Authors:
# Xenia Specka <xenia.specka@zalf.de>
# Michael Berg-Mohnicke <michael.berg@zalf.de>
#
# Maintainers:
# Currently maintained by the authors.
#
# This file has been created at the research platform input_data at ZALF.
# Copyright (C: Leibniz Centre for Agricultural Landscape Research (ZALF)


import json
import sys
import datetime
import csv
import time
import pandas as pd
from xlrd import open_workbook
import re
import os

col = {
    'year': 0,
    'day': 1,
    'globrad': 2,
    'tmax': 3,
    'tmin': 4,
    'rain': 5,
    'pan': 6
}

#############################################################
#############################################################
#############################################################


def generate_monica_climate_csv_files():

    input_dir = "CSIRO_data_set"
    output_dir = "climate_files/"

    met_files = get_met_files(input_dir)

    # iterate over every row/environment where row contains the setup of one simulation
    for filename in met_files:

        with open(input_dir + "/" + filename, "r") as csv_file:
            with open(output_dir + filename, "wb") as output_file:

                csv_out = csv.writer(output_file, delimiter=",")
                csv_out.writerow(["iso-date", "tmin", "tmax", "tavg", "globrad", "precip", "et0"])
                print filename, "---------------------------------------"

                is_data_row = False
                for row in csv_file:

                    data_row = row.split()
                    print len(data_row), data_row

                    if len(data_row) > 2 and data_row[0] == '()' and data_row[1] == '()':
                        is_data_row = True
                        continue

                    if is_data_row and len(data_row)>7:

                        year = data_row[col['year']]
                        julian_day = data_row[col['day']]

                        date = get_date(year, julian_day)
                        globrad = round(float(data_row[col['globrad']]), 5)
                        tmin = round(float(data_row[col['tmin']]), 2)
                        tmax = round(float(data_row[col['tmax']]), 2)
                        tavg = round(float(tmin + tmax) / 2.0, 2)
                        precip = round(float(data_row[col['rain']]), 3)
                        pan = round(float(data_row[col['pan']]), 3)
                        et0 = pan * 0.7

                        csv_out.writerow([date, tmin, tmax, tavg, globrad, precip, et0])


#############################################################
#############################################################
#############################################################


def get_met_files(dir_path):

    files = []
    for _file in os.listdir(dir_path):

        if _file.endswith(".met"):
            files.append(_file)
    return files


#############################################################
#############################################################
#############################################################

def get_date(year, julian_day):

    first_day = datetime.datetime(int(year), 1, 1)
    date = first_day + datetime.timedelta(int(julian_day)-1)
    return date.strftime("%Y-%m-%d")

#############################################################
#############################################################
#############################################################


if __name__ == "__main__":
    generate_monica_climate_csv_files()

