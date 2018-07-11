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

#############################################################
#############################################################
#############################################################

PATHS = {
    "specka": {
        "INCLUDE_FILE_BASE_PATH": "D:/Eigene Dateien specka/ZALF/devel/github/AgMIP_CALIBRATION/phase2/step1/"
    }
}

#############################################################
#############################################################
#############################################################


def run_producer():

    # some options and configurations
    create_simulation_files = True

    # calibration options
    training_mode = True
    calibrate_apache = True

    # simulation options
    activate_debug = False
    run_via_simulation_files = False
    output_dir = "runs/2018-07-09/"

    # calibration -------------------------------------
    # original "StageTemperatureSum": [[148, 284, 380, 180, 420, 25 ], "\u00b0C d"]
    stage1_sum = 120
    stage2_sum = 200 # 340
    stage3_sum = 550 # 407
    # ------------------------------------------------

    # based on Christian Kersebaums assumptions

    tsum_bbch55 = (stage2_sum + stage3_sum) - 180
    tsum_bbch30 = (stage3_sum - 180) * 0.25 + stage2_sum

    # overwrite some settings if creation of simulation files is active
    if create_simulation_files:
        run_via_simulation_files = False
        training_mode = False

    # technical initialisation
    config = {
        "user": "specka",
        "port": "66666",
        "server": "localhost"
    }

    sent_id = 0
    start_send = time.clock()
    socket = initialise_sockets(config)
    print(socket)

    # output file
    output_filename = "agmip_calibration_phase2_step1_evaluation.csv"
    if training_mode:
        output_filename = "agmip_calibration_phase2_step1_calibration.csv"

    paths = PATHS[config["user"]]

    # read in management information
    management_file = paths["INCLUDE_FILE_BASE_PATH"] + "monica_simulation_setup/input_data/cal2_phenology_mgt_soil_data.txt"
    management_df = pd.read_csv(management_file, sep='\t', header=0, index_col=None, keep_default_na=False,
                                encoding="latin1")

    # iterate over every row/environment where row contains the setup of one simulation
    for environment in management_df.iterrows():

        simulation_row = environment[1]
        sim_id = int(simulation_row["n"])

        # just for test runs stop after sending one element
        # if sent_id == 1 and create_simulation_files == False:
        # break

        if training_mode:
            # calibration mode
            if simulation_row["Date_observee_Epi_1cm"] == "NA":
                print("Skip evaluation simulation because testing mode is active")
                continue

            if calibrate_apache and simulation_row["Variete"] != "Apache":
                # calibration mode active but sim_id refers to wrong cultivar
                continue

        print("Run simulation " + str(sim_id))
        sim_parameters = None
        site_parameters = None
        crop_parameters = None

        if run_via_simulation_files:
            # run from existing simulation files
            print("Run from MONICA simulation files ...")

            simulation_dir = "monica_simulation_setup/calibration/"
            if simulation_row["Date_observee_Epi_1cm"] == "NA":
                simulation_dir = "monica_simulation_setup/evaluation/"

            with open(simulation_dir + "sim-" + str(sim_id) + ".json") as fp:
                sim_parameters = json.load(fp)

            with open(simulation_dir + "site-" + str(sim_id) + ".json") as fp:
                site_parameters = json.load(fp)

            with open(simulation_dir + "crop-" + str(sim_id) + ".json") as fp:
                crop_parameters = json.load(fp)

        else:
            # dynamically create simulation objects
            print("Dynamic run by creating simulation objects directly from AgMIP management file.")
            site_parameters = create_site_parameters(simulation_row)
            crop_parameters = create_crop_parameters(simulation_row)
            sim_parameters = create_sim_parameters(simulation_row, paths["INCLUDE_FILE_BASE_PATH"], sim_id, output_dir,
                                                   activate_debug, create_simulation_files, tsum_bbch30, tsum_bbch55 )

        if site_parameters is None:
            print("ERROR: site_parameters == None")
        if crop_parameters is None:
            print("ERROR: crop_parameters == None")
        if sim_parameters is None:
            print("ERROR: sim_parameters == None")

        # check if just MONICA simulation files should be created from the provided input files
        # do'nt send any information if input files should be created
        if create_simulation_files:
            dir = "monica_simulation_setup/calibration/"
            if simulation_row["Date_observee_Epi_1cm"] == "NA":
                dir="monica_simulation_setup/evaluation/"

            with open(dir + "site-" + str(sim_id) + ".json", "w") as fp:
                json.dump(site_parameters, fp=fp, indent=4)

            with open(dir + "crop-" + str(sim_id) + ".json", "w") as fp:
                json.dump(crop_parameters, fp=fp, indent=4)

            with open(dir + "sim-" + str(sim_id) + ".json", "w") as fp:
                json.dump(sim_parameters, fp=fp, indent=4)
            continue

        env_map = {
            "crop": crop_parameters,
            "site": site_parameters,
            "sim": sim_parameters
        }
        env = monica_io.create_env_json_from_json_config(env_map)


        # calibration

        # for calibration overwrite stage temperature sum values
        env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"]["StageTemperatureSum"][0][1] = stage2_sum

        env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"]["StageTemperatureSum"][0][
            2] = stage3_sum

        env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"]["StageTemperatureSum"][0][
            0] = stage1_sum

        temp_sum = env["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"]["cultivar"]["StageTemperatureSum"][0]
        bbch30_tempsum = temp_sum[0] + temp_sum[1] + 0.25 * (temp_sum[3])

        # final env object with all necessary information
        env["customId"] = {
            "id": sim_id,
            "calibration": training_mode,
            "sim_dir": output_dir,
            "output_filename": output_filename,
            "cultivar": simulation_row["Variete"],
            "sowing_date": simulation_row["Date_Semis"],
            "bbch30": simulation_row["Date_observee_Epi_1cm"],      # observation bbch 30
            "bbch55": simulation_row["Date_observee_Epiaison"],     # observation bbch 55
            "site": simulation_row["Libelle"]
        }

        with open("monica_simulation_setup/env.json", "w") as fp:
            json.dump(env, fp=fp, indent=4)


        # sending env object to MONICA ZMQ
        print("sent env ", sent_id, " customId: ", env["customId"])
        socket.send_json(env)
        sent_id += 1

    stop_send = time.clock()

    # just tell the sending time if objects have really been sent
    if not create_simulation_files:
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


def get_climate_information():

    """ Setups static information about climate files of the study. """
    #
    climate_csv_config = {
        "no-of-climate-file-header-lines": 1,
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

    # climate file setup
    elevation = str(mgt_row["Altitude"])
    climate_csv_config, climate_file_map = get_climate_information()

    sim_parameters["climate.csv-options"] = climate_csv_config
    sim_parameters["climate.csv-options"]["start-date"] = sim_parameters["start-date"]
    sim_parameters["climate.csv-options"]["end-date"] = sim_parameters["end-date"]

    climate_path = include_path + "monica_simulation_setup/input_data/climate/" + climate_file_map[elevation]
    sim_parameters["climate.csv"] = climate_path
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
        irrigation_step = {"date": date, "type": "Irrigation", "amount": [dose, "mm"]}
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

