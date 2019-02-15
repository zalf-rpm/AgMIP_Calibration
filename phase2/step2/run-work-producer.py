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
sys.path.append("C:\\Users\\specka\\AppData\\Local\\MONICA")
import datetime
import time
import zmq
import monica_io
import pandas as pd
import os

#############################################################
#############################################################
#############################################################

PATHS = {
    "specka": {
        "INCLUDE_FILE_BASE_PATH": "D:/Eigene Dateien specka/ZALF/devel/github/AgMIP_CALIBRATION/phase2/step2/"
    }
}

#############################################################
#############################################################
#############################################################


def run_producer():

    # calibration options
    calibration_mode = False

    # simulation options
    activate_debug = False

    output_dir = "runs/2019-02-15/"

    # calibration -------------------------------------

    # technical initialisation
    config = {
        "user": "specka",
        "port": "66666",
        "server": "localhost"
    }

    paths = PATHS[config["user"]]

    sent_id = 0
    start_send = time.clock()
    socket = initialise_sockets(config)
    print(socket)

    # output file
    output_filename = "agmip_calibration_phase2_step2_evaluation.csv"

    if calibration_mode:
        output_filename = "agmip_calibration_phase2_step2_calibration.csv"


    # read in management information
    management_file = paths["INCLUDE_FILE_BASE_PATH"] + "info/CSIRO_data_set/simulation_plan.xlsx"
    management_df = pd.read_excel(management_file, sheader=0, index_col=None, keep_default_na=False,
                                  encoding="latin1")

    print "Shape", management_df.shape

    # iterate over every row/environment where row contains the setup of one simulation
    for sim_row, environment in management_df.iterrows():

        print "Run simulation " + str(sim_row)

        id = int(environment["ID"])
        calibration_mode = bool(environment["Calibration"])
        year = int(environment["Year"])
        site_name = environment["Site"]
        sowing_day = environment["sowDay"]

        sim_parameters = None
        site_parameters = None
        crop_parameters = None

        simulation_dir = "monica_simulation_setup/evaluation"
        if calibration_mode:
            simulation_dir = "monica_simulation_setup/calibration"

        sim_file = "sim-%d.json" % id
        with open(simulation_dir + "/" + sim_file) as fp:
            sim_parameters = json.load(fp)

        site_file = sim_parameters["site.json"]

        with open(site_file) as fp:
            site_parameters = json.load(fp)

        #site_parameters["include-file-base-path"] = paths["INCLUDE_FILE_BASE_PATH"]
        sim_parameters["include-file-base-path"] = paths["INCLUDE_FILE_BASE_PATH"]

        # spring wheat parameters for stage temperature sum
        stage1_sum = 142.74
        stage2_sum = 218.43
        stage3_sum = 302.21
        stage4_sum = 67.51
        stage5_sum = 273.15


        tsum_zadok30 =  stage2_sum + (stage3_sum * 0.25)
        tsum_zadok65 = stage2_sum + stage3_sum + (stage4_sum * 0.25)

        output_map = {

            "events": [
                "anthesis", [
                    "Date|Ant"
                ],
                "maturity", [
                    "Date|Mat",
                ],
                ["while", "Stage", "=", 2], [
                    ["Date|EmergeDate", "FIRST"]
                ],
                ["while", "Stage", "=", 3], [
                    ["Date|BeginStage3", "FIRST"]
                ],
                ["while", "Stage", "=", 4], [
                    ["Date|BeginStage4", "FIRST"]
                ],
                ["while", "Stage", "=", 5], [
                    ["Date|BeginStage5", "FIRST"]
                ],
                ["while", "Stage", "=", 6], [
                    ["Date|BeginStage6", "FIRST"]
                ],
                ["while", "TempSum", ">=", tsum_zadok30], [
                    ["Date|ZADOK30", "FIRST"]
                ],
                ["while", "TempSum", ">=", tsum_zadok65], [
                    ["Date|ZADOK65", "FIRST"]
                ],
                ["while", "Stage", "=", 6], [
                    ["Date|ZADOK90", "FIRST"]
                ]
            ]
        }

        sim_parameters["output"] = output_map

        crop_file = sim_parameters["crop.json"]
        with open(crop_file) as fp:
            crop_parameters = json.load(fp)

        env_map = {
            "crop": crop_parameters,
            "site": site_parameters,
            "sim": sim_parameters,
            "climate": ""
        }

        env = monica_io.create_env_json_from_json_config(env_map)

        env["csvViaHeaderOptions"] = sim_parameters["climate.csv-options"]
        env["csvViaHeaderOptions"]["start-date"] = sim_parameters["climate.csv-options"]["start-date"]
        env["csvViaHeaderOptions"]["end-date"] = sim_parameters["climate.csv-options"]["end-date"]
        env["pathToClimateCSV"] = sim_parameters["climate.csv"]

        # overwrite stage temperature sum values with tommaso's calibrated ones
        # stage 1
        env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"]\
            ["StageTemperatureSum"][0][0] = stage1_sum

        env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"]\
            ["StageTemperatureSum"][0][1] = stage2_sum

        env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"] \
            ["StageTemperatureSum"][0][2] = stage3_sum

        env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"] \
            ["StageTemperatureSum"][0][3] = stage4_sum

        env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"] \
            ["StageTemperatureSum"][0][4] = stage5_sum


        # final env object with all necessary information
        env["customId"] = {
            "id": id,
            "calibration": calibration_mode,
            "output_dir": output_dir,
            "output_filename": output_filename,
            "sowing_day": sowing_day,
            "site_name": site_name,
            "year": year
        }

        with open("monica_simulation_setup/env.json", "w") as fp:
            json.dump(env, fp=fp, indent=4)


        # sending env object to MONICA ZMQ
        print("sent env ", sent_id, " customId: ", env["customId"])
        socket.send_json(env)
        sent_id += 1

        # break

    stop_send = time.clock()

    # just tell the sending time if objects have really been sent

    print("sending ", sent_id, " envs took ", (stop_send - start_send), " seconds")


#############################################################
#############################################################
#############################################################

def initialise_sockets(config):

    """ Initialises the socket based on command line parameter information"""

    context = zmq.Context()
    socket = context.socket(zmq.PUSH)

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            k, v = arg.split("=")
            if k in config:
                config[k] = v

    socket.connect("tcp://" + config["server"] + ":" + str(config["port"]))
    return socket



#############################################################
#############################################################
#############################################################


if __name__ == "__main__":
    run_producer()

