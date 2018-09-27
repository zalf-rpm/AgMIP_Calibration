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

    output_dir = "runs/2018-09-27/"

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

        sim_file = "sim-%d.json" % (id)
        with open(simulation_dir + "/" + sim_file) as fp:
            sim_parameters = json.load(fp)

        sim_parameters["include-file-base-path"] = paths["INCLUDE_FILE_BASE_PATH"]

        site_file = sim_parameters["site.json"]
        with open(site_file) as fp:
            site_parameters = json.load(fp)

        crop_file = sim_parameters["crop.json"]
        with open(crop_file) as fp:
            crop_parameters = json.load(fp)

        env_map = {
            "crop": crop_parameters,
            "site": site_parameters,
            "sim": sim_parameters
        }

        # print "******************************************"
        # print crop_parameters
        # print "******************************************"
        # print site_parameters
        # print "******************************************"
        # print sim_parameters
        env = monica_io.create_env_json_from_json_config(env_map)

        # calibration

        # for calibration overwrite stage temperature sum values

        # final env object with all necessary information
        env["customId"] = {
            "id": id,
            "calibration": calibration_mode,
            "sim_files": output_dir,
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


        break

    stop_send = time.clock()

    # just tell the sending time if objects have really been sent

    print("sending ", sent_id, " envs took ", (stop_send - start_send), " seconds")

#############################################################
#############################################################
#############################################################


def get_simulation_files(dir_path):

    files = []
    for _file in os.listdir(dir_path):

        if _file.startswith("sim-") and _file.endswith(".json") :
            files.append(dir_path + "/" +  _file)
    return files

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


def get_climate_information():

    """ Setups static information about climate_files files of the study. """
    #
    climate_csv_config = {
        "no-of-climate_files-file-header-lines": 1,
        "csv-separator": ",",
        "header-to-acd-names": {
            "et0": "et0"
        }
    }

    climate_file_map = {
        "73": "climate_2590.csv",
        "87": "climate_10170.csv",
        "206": "climate_21110.csv",
        "153": "climate_27110.csv",
        "129": "climate_41240.csv",
        "93": "climate_56500.csv",
        "109": "climate_91720.csv"
    }

    return climate_csv_config, climate_file_map

#############################################################
#############################################################
#############################################################


def get_monica_date_string(date):

    """ Converts a date string provide by the AgMIP Mgt File into a MONICA date string (isoformat). """

    if date == "NA":
        return "NA"

    new_date = datetime.datetime.strptime(date, "%d/%m/%Y").strftime("%Y-%m-%d")
    return new_date

#############################################################
#############################################################
#############################################################


def create_sim_parameters(mgt_row, include_path, sim_id, output_dir, activate_debug, create_files, tsum_30, tsum_55):

    """ Creates simulation object based on information provided by the Agmip files. """

    sim_parameters = {}

    # simulation start and end
    harvest_year = int(mgt_row["Annee_Recolte"])
    sim_parameters["start-date"] = str(harvest_year-1) + "-08-01"
    sim_parameters["end-date"] = str(harvest_year) + "-12-31"
    sim_parameters["use-leap-years"] = True

    if create_files:
        sim_parameters["crop.json"] = "crop-" + str(sim_id) + ".json"
        sim_parameters["site.json"] = "site-" + str(sim_id) + ".json"

    sim_parameters["debug?"] = activate_debug

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
            ["while", "TempSum", ">=", tsum_30], [
                ["Date|BBCH30", "FIRST"]
            ],
            ["while", "TempSum", ">=", tsum_55], [
                ["Date|BBCH55", "FIRST"]
            ],
            ["while", "Stage", "=", 3], [
                ["DOY|Stage3DOY", "FIRST"]
            ],
            ["while", "Stage", "=", 4], [
                ["DOY|Stage4DOY", "FIRST"]
            ]
        ]
    }

    sim_parameters["output"] = output_map

    sim_parameters["NumberOfLayers"] = 20
    sim_parameters["LayerThickness"] = [0.1, "m"]
    sim_parameters["UseSecondaryYields"] = True
    sim_parameters["NitrogenResponseOn"] = True
    sim_parameters["WaterDeficitResponseOn"] = True
    sim_parameters["EmergenceMoistureControlOn"] = False
    sim_parameters["EmergenceFloodingControlOn"] = False
    sim_parameters["UseAutomaticIrrigation"] = False
    sim_parameters["UseNMinMineralFertilisingMethod"] = False

    # climate_files file setup
    elevation = str(mgt_row["Altitude"])
    climate_csv_config, climate_file_map = get_climate_information()

    sim_parameters["climate_files.csv-options"] = climate_csv_config
    sim_parameters["climate_files.csv-options"]["start-date"] = sim_parameters["start-date"]
    sim_parameters["climate_files.csv-options"]["end-date"] = sim_parameters["end-date"]

    climate_path = include_path + "monica_simulation_setup/input_data/climate_files/" + climate_file_map[elevation]
    sim_parameters["climate_files.csv"] = climate_path
    sim_parameters["include-file-base-path"] = include_path

    return sim_parameters

#############################################################
#############################################################
#############################################################


def create_crop_parameters(mgt_row):

    """ Creates a crop simulation object based on information of the Agmip mgt file. """

    species = mgt_row["Espece"]
    cultivar = mgt_row["Variete"]

    crop_species = None
    crop_variety = None
    crop_name = "."

    if species == "Ble_tendre_d'hiver":
        crop_species = "WW"
        crop_name = "wheat"

    if cultivar == "Apache":
        crop_variety = "winter-wheat-apache"
    elif cultivar == "Bermude":
        crop_variety = "winter-wheat-bermude"
    else:
        print("Error: Unknown variety found. Stopping simulation now.")
        sys.exit(-1)

    workstep_list = []
    workstep_list.append({"date": get_monica_date_string(mgt_row["Date_Semis"]), "type": "Sowing", "crop": ["ref", "crops", crop_species]})

    # Irrigation steps ----------------------------
    number_of_irrigation_events = int(mgt_row['Nombre_Irrigation'])
    for event in range(1, number_of_irrigation_events + 1):
        date = get_monica_date_string(mgt_row["Date_" + str(event) + "_Irrigation"])
        dose = float(mgt_row["Dose_" + str(event) + "_Irrigation"])
        irrigation_step = {
            "date": date,
            "type": "Irrigation",
            "amount": [dose, "mm"],
            "parameters": {
                "nitrateConcentration": [0.0, "mg dm-3"],
                "sulfateConcentration": [0.0, "mg dm-3"]
            }
        }
        workstep_list.append(irrigation_step)

    # fertilization steps -------------------------
    fertilizer_map = {
        "Ammonitrate": "monica_simulation_setup/monica_parameters/mineral-fertilisers/AN.json",
        "Solution_azotee": "monica_simulation_setup/monica_parameters/mineral-fertilisers/U.json",
        "18_46": "monica_simulation_setup/monica_parameters/mineral-fertilisers/AP.json"
    }

    number_of_fertilizer_applications = int(mgt_row["Nombre_Fertilisation_azotee"])
    for fert_application in range(1, number_of_fertilizer_applications + 1):
        date = get_monica_date_string(mgt_row["Date_" + str(fert_application) + "_Fertilisation_azotee"])
        dose = float(mgt_row["Dose_" + str(fert_application) + "_Fertilisation_azotee"])
        fertiliser_type = mgt_row["Produit_"  + str(fert_application) + "_Fertilisation_azotee"]

        fertiliser_step = {
            "date": date,
            "type": "MineralFertilization",
            "amount": [dose, "kg N"],
            "partition": ["include-from-file", fertilizer_map[fertiliser_type]]
        }
        workstep_list.append(fertiliser_step)

    # harvest step -------------------------------
    harvest_step = {
        "type": "AutomaticHarvest",
        "latest-date": "0001-09-01",
        "min-%-asw": 0,
        "max-%-asw": 100,
        "max-3d-precip-sum": 5,
        "max-curr-day-precip": 1,
        "harvest-time": "maturity"
    }
    workstep_list.append(harvest_step)

    # test to externally set ET0
    # harvest_year = int(mgt_row["Annee_Recolte"])
    # start_date = datetime.datetime(day=1, month=8, year=harvest_year-1)
    # end_date = datetime.datetime(day=31, month=12, year=harvest_year)
    # for date in daterange(start_date, end_date):
    #        workstep_list.append({"type": "SetValue", "date": date.strftime("%Y-%m-%d"), "var": "ET0", "value": ["=", 0.5]})

    crop_parameters = {
        "crops" : {
            crop_species: {
                "is-winter-crop": True,
                "cropParams": {
                    "species": ["include-from-file", "monica_simulation_setup/monica_parameters/crops/" + crop_name + ".json"],
                    "cultivar": ["include-from-file", "monica_simulation_setup/monica_parameters/crops/" + crop_name + "/" + crop_variety + ".json"]
                },
                "residueParams": ["include-from-file", "monica_simulation_setup/monica_parameters/crop-residues/" + crop_name + ".json"]
            }
        },
        "cropRotation": [{"worksteps": workstep_list}],
        "CropParameters": {
            "=": ["include-from-file", "monica_simulation_setup/monica_parameters/general/crop.json"]
        }
    }


    return crop_parameters

#############################################################
#############################################################
#############################################################

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)


def create_site_parameters(mgt_row):

    """ Extract site parameters in MONICA style from AgMIP Calibration management file. """

    site = {}
    site_parameters = {
        "Latitude": float(mgt_row['Latitude']),
        "Slope": 0.01,                          #???
        "HeightNN": [float(mgt_row['Altitude']), "m"],
        "NDeposition": [30, "kg N ha-1 y-1"]
    }

    # Soil Parameters per Horizona
    number_of_horizons = mgt_row['N_Horizons']

    soil_profile_parameter_list = []
    for horizon in range(1,number_of_horizons + 1):
        suffix="_H%d" % horizon

        fc = round(float(mgt_row["Hcc" + suffix]) / 100.0, 3)
        pwp = round(float(mgt_row["H_pFp" + suffix]) / 100.0, 3)

        soil_profile_parameter = {
            "Thickness": [float(mgt_row["Epaisseur" + suffix]), "cm"],
            "Sceleton": float(mgt_row["Cailloux" + suffix])/100.0,
            "Sand": (float(mgt_row["Sable_fin" + suffix]) + float(mgt_row["Sable_grossier" + suffix])) / 100.0,
            "Clay": float(mgt_row["Argile" + suffix]) / 100.0,
            "PermanentWiltingPoint": pwp,
            "FieldCapacity": fc,
            "SoilOrganicMatter": float(mgt_row["Matiere_Organique" + suffix]) / 100.0,
            "SoilBulkDensity": float(mgt_row["Da_terre_fine" + suffix]) * 1000.0,
            "pH": float(mgt_row["pH_eau" + suffix])
        }

        if horizon == 1:
            soil_profile_parameter["SoilMoisturePercentFC"] = 0
        else:
            soil_profile_parameter["SoilMoisturePercentFC"] = round((pwp/fc) * 100.0,2)

        soil_profile_parameter_list.append(soil_profile_parameter)

    site_parameters["SoilProfileParameters"] = soil_profile_parameter_list

    site["SiteParameters"] = site_parameters

    # additional MONICA parameters
    site["SoilTemperatureParameters"] = ["include-from-file", "monica_simulation_setup/monica_parameters/general/soil-temperature.json"]
    site["EnvironmentParameters"] = {
                                 "=": ["include-from-file", "monica_simulation_setup/monica_parameters/general/environment.json"],
                                 "LeachingDepth": 2.0,
                                 "WindSpeedHeight": 2.5,
                                 "AtmosphericCO2": 395
                             }
    site["SoilOrganicParameters"] = ["include-from-file", "monica_simulation_setup/monica_parameters/general/soil-organic.json"]
    site["SoilTransportParameters"] = ["include-from-file", "monica_simulation_setup/monica_parameters/general/soil-transport.json"]
    site["SoilMoistureParameters"] = ["include-from-file", "monica_simulation_setup/monica_parameters/general/soil-moisture.json"]

    return site

#############################################################
#############################################################
#############################################################


if __name__ == "__main__":
    run_producer()

