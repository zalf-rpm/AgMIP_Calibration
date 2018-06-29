#!/usr/bin/python
# -*- coding: UTF-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/. */

# Authors:
# Michael Berg-Mohnicke <michael.berg@zalf.de>
#
# Maintainers:
# Currently maintained by the authors.
#
# This file has been created at the Institute of
# Landscape Systems Analysis at the ZALF.
# Copyright (C: Leibniz Centre for Agricultural Landscape Research (ZALF)

import sys
#sys.path.insert(0, "C:\\Users\\berg.ZALF-AD\\GitHub\\monica\\project-files\\Win32\\Release")
#sys.path.insert(0, "C:\\Users\\berg.ZALF-AD\\GitHub\\monica\\src\\python")
#print sys.path

#import ascii_io
#import json
import csv
import types
import os
from datetime import datetime
from collections import defaultdict


import zmq
import monica_io
#print zmq.pyzmq_version()

PATHS = {
    "specka": {
        "local-path-to-output-dir": "results/"
    }
}

#############################################################
#############################################################
#############################################################

"""

"""
def run_consumer():
    "collect input_data from workers"

    config = {
        "user": "specka",
        "port": "77776",
        "server": "localhost"
    }
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            k,v = arg.split("=")
            if k in config:
                config[k] = v

    paths = PATHS[config["user"]]

    received_env_count = 1
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://" + config["server"] + ":" + config["port"])
    socket.RCVTIMEO = 1000
    leave = False
    write_normal_output_files = True

    while not leave:

        try:
            result = socket.recv_json(encoding="latin-1")
        except:
            continue

        if result["type"] == "finish":
            print("Received finish message")
            leave = True

        elif not write_normal_output_files:

            print("Received work result 2 - ", received_env_count, " customId: ", result["customId"])
            write_bcd_output_file(result)
            received_env_count += 1

        elif write_normal_output_files:

            #print("Received work result 1 - ", received_env_count, " customId: ", result["customId"])
            #write_bcd_output_file(result)

            print ("received work result ", received_env_count, " customId: ", str(
                result.get("customId", "").values()))

            custom_id = result["customId"]


            output_file = custom_id["sim_dir"] + custom_id["output_filename"]


            # with open("out/out-" + str(i) + ".csv", 'wb') as _:
            with open(output_file, 'wb') as _:
                writer = csv.writer(_, delimiter=",")

                for data_ in result.get("input_data", []):
                    results = data_.get("results", [])
                    orig_spec = data_.get("origSpec", "")
                    output_ids = data_.get("outputIds", [])

                    if len(results) > 0:
                        writer.writerow([orig_spec.replace("\"", "")])
                        for row in monica_io.write_output_header_rows(output_ids,
                                                                      include_header_row=True,
                                                                      include_units_row=True,
                                                                      include_time_agg=False):
                            writer.writerow(row)

                        for row in monica_io.write_output(output_ids, results):
                            writer.writerow(row)

                    writer.writerow([])


            received_env_count += 1


########################################################################
########################################################################
########################################################################

"""
Analyses result object, creates a map with yearly results and then
writes them to filesystem. Output filename is passed with custom_id object.
"""
def write_bcd_output_file(result):

    custom_id = result["customId"]
    site_name = custom_id["site"]
    print ("Received results from %s" % custom_id["output_filename"])

    with open("out/2018-06-26/" + custom_id["output_filename"], 'wb') as fp:
        writer = csv.writer(fp, delimiter="\t")
        writer.writerow(["BCD3_2017"])
        writer.writerow(["Model: MO"])
        writer.writerow(["Modeler_name: Xenia Specka"])
        writer.writerow(["Simulation:"])
        writer.writerow(["Site: " + site_name])
        writer.writerow(["Model", "Info", "Year", "Yield", "Biom-an", "Biom-ma", "MaxLAI", "Ant", "Mat",
                         "Nleac", "WDrain", "CroN-an", "CroN-ma", "GrainN", "GNumber", "CumET", "Nmin",
                         "Nvol", "Nimmo", "Nden", "SoilAvW", "SoilN", "PET", "Transp"])
        writer.writerow(["CodeN", "level", "season", "(t/ha)", "(t/ha)", "(t/ha)", "(-)", "(DOY)", "(DOY)",
                         "kgN/ha", "(mm)", "kgN/ha", "kgN/ha", "kgN/ha", "(/m2)", "(mm)", "kgN/ha", "kgN/ha",
                         "kgN/ha", "kgN/ha", "(mm)", "kgN/ha", "(mm)", "(mm)"])

        year_to_vals = defaultdict(dict)
        for data in result.get("input_data", []):

            results = data.get("results", [])
            oids = data.get("outputIds", [])

            # skip empty results, e.g. when event condition haven't been met
            if len(results) == 0:
                continue

            assert len(oids) == len(results)
            for kkk in range(0, len(results[0])):
                vals = {}

                for iii in range(0, len(oids)):

                    oid = oids[iii]
                    #print(oid)

                    val = results[iii][kkk]

                    name = oid["name"] if len(oid["displayName"]) == 0 else oid["displayName"]

                    if isinstance(val, types.ListType):
                        for val_ in val:
                            vals[name] = val_
                    else:
                        vals[name] = val

                #print(vals)

                if "Year" not in vals:
                    print("Missing Year in result section. Skipping results section.")
                    continue

                year_to_vals[vals["Year"]].update(vals)

        rows = create_output_rows(year_to_vals)
        for row in rows:
            writer.writerow(row)

########################################################################
########################################################################
########################################################################

"""
Creates array with output rows in BCD output style
"""
def create_output_rows(result_map):

    rows = []

    for year in sorted(result_map.keys()):

        values = result_map[year]

        row = ["MO", "na"]
        row.append(values["Year"])

        row.append(round(float(values["Yield"]) / 1000.0, 2)) # kg ha-1 --> t ha-1

        if "Biom-ma" not in values:
            print(year)
            for k, v in values:
                print(k, ":", v)

        row.append(round(float(values["Biom-an"]) / 1000.0, 2))

        if "Biom-ma" not in values:
            print(year)
            for k,v in values:
                print(k, ":", v)
        row.append(round(float(values["Biom-ma"]) / 1000.0, 2))

        row.append(round(float(values["MaxLAI"]),2))
        row.append(values["Ant"])
        row.append(values["Mat"])

        row.append(round(float(values["Nleac"]), 2))
        row.append(round(float(values["WDrain"]), 2))

        row.append(round(float(values["CroN-ma"]), 2))
        row.append(round(float(values["CroN-an"]),2))
        row.append(round(float(values["GrainN"]), 2))

        row.append("na") # GNumber
        row.append(round(float(values["CumET"]),2))
        row.append(round(float(values["Nmin"]), 2))
        row.append(round(float(values["Nvol"]),2))

        row.append("na") # Nimmo
        row.append(round(float(values["Nden"]) / 1000.0, 2))
        pasw = float(values["PASW"]) * 1000.0 * 0.1 # m³ / m³ --> mm
        row.append(round(pasw,2))

        nmin = (float(values["NO3"]) + float(values["NH4"])) * 0.1 * 10000.0 # --> kg m2 --> kg ha-1
        row.append(round(nmin,2))
        row.append(round(float(values["PET"]),2))
        row.append(round(float(values["Transp"]),2))

        rows.append(row)

    return rows



if __name__ == "__main__":
    run_consumer()

