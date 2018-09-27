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
# sys.path.insert(0,"C:\\Program Files (x86)\\MONICA")
#sys.path.insert(0, "D:\\Eigene Dateien specka\\ZALF\\devel\\github\\monica-master\\monica\\project-files\\Win32\\Release")
#sys.path.insert(0, "D:\\Eigene Dateien specka\\ZALF\devel\\github\\monica-master\\monica\\src\\python")
sys.path.append("C:\\Users\\specka\\AppData\\Local\\MONICA")
#print sys.path

import csv
import types
import os
import datetime

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
    write_normal_output_files = False

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
            write_agmip_calibration_output_file(result)
            received_env_count += 1

        elif write_normal_output_files:

            #print("Received work result 1 - ", received_env_count, " customId: ", result["customId"])
            #write_agmip_calibration_output_file(result)
            print("\n")
            print ("received work result ", received_env_count, " customId: ", str(result.get("customId", "").values()))


            custom_id = result["customId"]
            output_file = custom_id["sim_files"] + custom_id["output_filename"]
            print(result)

            print("Write output file:", output_file)
            with open(output_file, 'wb') as _:
                writer = csv.writer(_, delimiter=",")

                for data_ in result.get("data", []):
                    print("Data", data_)

                    results = data_.get("results", [])
                    orig_spec = data_.get("origSpec", "")
                    output_ids = data_.get("outputIds", [])
                    print("Results:", results)
                    if len(results) > 0:
                        writer.writerow([orig_spec.replace("\"", "")])
                        for row in monica_io.write_output_header_rows(output_ids,
                                                                      include_header_row=True,
                                                                      include_units_row=False,
                                                                      include_time_agg=False):
                            writer.writerow(row)

                        for row in monica_io.write_output(output_ids, results):
                            #print(row)
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
def write_agmip_calibration_output_file(result):

    custom_id = result["customId"]

    id = custom_id["id"]

    output_file = custom_id["sim_files"] + custom_id["output_filename"]

    fp=None

    # if os.path.exists(output_file):
    #     os.remove(output_file)
    #     fp = open(output_file, 'wb')
    # else:
    fp = open(output_file, 'ab')

    writer = csv.writer(fp, delimiter="\t")
    if id == 1:
        writer.writerow(["Year", "Site", "sowDay", "simulatedZadok10_dd/mm/yyyy", "simulatedZadok30_dd/mm/yyyy",
                         "simulatedZadok65_dd/mm/yyyy", "simulatedZadok90_dd/mm/yyyy"])

    sim_results = {}
    print ("Received results from %s" % custom_id["output_filename"])

    for output_section in result.get("data", []):

        results = output_section.get("results", [])
        output_ids = output_section.get("outputIds", [])

        # skip empty results, e.g. when event condition haven't been met
        if len(results) == 0:
            continue

        assert len(output_ids) == len(results)
        for kkk in range(0, len(results[0])):

            for iii in range(0, len(output_ids)):

                oid = output_ids[iii]
                val = results[iii][kkk]
                name = oid["name"] if len(oid["displayName"]) == 0 else oid["displayName"]

                if isinstance(val, types.ListType):
                    for val_ in val:
                        sim_results[name] = val_
                else:
                    sim_results[name] = val

    print(sim_results)
    writer.writerow(create_output_rows(id, sim_results, custom_id))

    end_id = 70

    # if sim_id == end_id:
    #     global global_bbch30
    #     global global_bbch55
    #     writer.writerow([None, global_bbch30, global_bbch55])

    del writer
    fp.close()



########################################################################
########################################################################
########################################################################


def create_output_rows(sim_id, result_map, custom_id):

    """ Creates array with output rows in the required AgMIP output style. """

    calibration_mode = custom_id["calibration"]
    sowing_day = custom_id["sowing_day"]
    site_name = custom_id["site_name"]
    year = custom_id["year"]

    row = [year, site_name, sowing_day]

    # date of emergence
    # emerge_date = datetime.datetime.strptime(result_map["EmergeDate"], '%Y-%m-%d')
    # row.append(emerge_date.strftime("%d/%m/%Y"))

    # date bbch30
    # bbch30 = datetime.datetime.strptime(result_map["BBCH30"], '%Y-%m-%d')
    # row.append(bbch30.strftime("%d/%m/%Y"))
    #
    #
    # bbch55 = datetime.datetime.strptime(result_map["BBCH55"], '%Y-%m-%d')
    # row.append(bbch55.strftime("%d/%m/%Y"))
    #
    # ignore_simulations = [] # 57 for apache?
    # if calibration and sim_id not in ignore_simulations:
    #
    #     bbch30_obs = datetime.datetime.strptime(bbch_30_observed, '%d/%m/%Y')
    #     bbch55_obs = datetime.datetime.strptime(bbch_55_observed, '%d/%m/%Y')
    #     diff_bbch30 = bbch30_obs - bbch30
    #     diff_bbch55 = bbch55_obs - bbch55
    #     row.append(diff_bbch30.days)
    #     row.append(diff_bbch55.days)
    #
    #     global global_bbch30
    #     global global_bbch55
    #
    #     global_bbch30 += diff_bbch30.days
    #     global_bbch55 += diff_bbch55.days
    #
    #     stage3_doy = result_map["Stage3DOY"]
    #     bbch30_doy = bbch30.timetuple().tm_yday
    #     stage4_doy = result_map["Stage4DOY"]
    #     bbch55_doy = bbch55.timetuple().tm_yday
    #
    #     row.append(stage3_doy)
    #     row.append(bbch30_doy)
    #     row.append(bbch30_obs.timetuple().tm_yday)
    #     row.append(stage3_doy<bbch30_doy)
    #     row.append(stage4_doy)
    #     row.append(bbch55_doy)
    #     row.append(bbch55_obs.timetuple().tm_yday)
    #     row.append(bbch55_doy<stage4_doy)



    # anthesis_date
    #ant_date = datetime.datetime.strptime(result_map["Ant"], '%Y-%m-%d')
    #row.append(ant_date.strftime("%d/%m/%Y"))

    # maturity_date
    #mat_date = datetime.datetime.strptime(result_map["Mat"], '%Y-%m-%d')
    #row.append(mat_date.strftime("%d/%m/%Y"))

    return row

########################################################################
########################################################################
########################################################################


global_bbch30 = 0
global_bbch55 = 0


if __name__ == "__main__":
    run_consumer()

