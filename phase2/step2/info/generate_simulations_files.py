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
import datetime
import pandas as pd

activate_debug = True

#############################################################
#############################################################
#############################################################


def generate_sim_and_crop_files():

    output_dir = "sim_files/"
    calibration_dir = output_dir + "calibration/"
    evaluation_dir = output_dir + "evaluation/"

    management_file = "CSIRO_data_set/simulation_plan.xlsx"
    management_df = pd.read_excel(management_file, sheader=0, index_col=None, keep_default_na=False,
                                encoding="latin1")
    #print management_df

    for row_index, simulation_row in management_df.iterrows():

        #print"###1", simulation_row
        sim_id = simulation_row["ID"]

        destination_dir = calibration_dir
        print "Evaluation", simulation_row["Calibration"]
        if bool(simulation_row["Calibration"]):
            destination_dir = calibration_dir
        else:
            destination_dir = evaluation_dir

        sim = create_sim_parameters(simulation_row, "", sim_id, bool(simulation_row["Calibration"]))
        with open(destination_dir + "sim-" + str(sim_id) + ".json", "w") as fp:
            json.dump(sim, fp=fp, indent=4)

        crop_file = create_crop_parameters(simulation_row)
        with open(destination_dir + "/crop-" + str(sim_id) + ".json", "w") as fp:
            json.dump(crop_file, fp=fp, indent=4)


#############################################################
#############################################################
#############################################################

def get_monica_date_string(date):

    """ Converts a date string provide by the AgMIP Mgt File into a MONICA date string (isoformat). """

    if date == "NA":
        return "NA"

    try:

        new_date = datetime.datetime.strptime(date, "%d/%m/%Y").strftime("%Y-%m-%d")
        return new_date
    except ValueError:
        pass

    try:
        new_date = datetime.datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")
        return new_date
    except ValueError:
        pass


    return new_date

#############################################################
#############################################################
#############################################################


def create_sim_parameters(mgt_row, include_path, sim_id, calibration_mode):

    """ Creates simulation object based on information provided by the Agmip files. """

    sim_parameters = {}
    #
    # # simulation start and end
    harvest_year = int(mgt_row["Year"])
    sim_parameters["start-date"] = str(harvest_year) + "-01-01"
    sim_parameters["end-date"] = str(harvest_year) + "-12-31"
    sim_parameters["use-leap-years"] = True

    sim_parameters["crop.json"] = "./" + "monica_simulation_setup/evaluation/crop-" + str(sim_id) + ".json"
    if calibration_mode:
        sim_parameters["crop.json"] = "./" + "monica_simulation_setup/calibration/crop-" + str(sim_id) + ".json"

    sim_parameters["site.json"] = "./" + "monica_simulation_setup/sites/" + mgt_row["Site_file"]
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
    elevation = "0.0"
    climate_csv_config = {
        "no-of-climate_files-file-header-lines": 1,
        "csv-separator": " ",
        "header-to-acd-names": {
            "et0": "et0"
        }
    }

    sim_parameters["climate_files.csv-options"] = climate_csv_config
    sim_parameters["climate_files.csv-options"]["start-date"] = sim_parameters["start-date"]
    sim_parameters["climate_files.csv-options"]["end-date"] = sim_parameters["end-date"]
    # +
    climate_path = "D:/Eigene Dateien specka/ZALF/devel/github/AgMIP_CALIBRATION/phase2/step2/monica_simulation_setup/climate/" + mgt_row["climate_file"]
    sim_parameters["climate_files.csv"] = climate_path
    #sim_parameters["include-file-base-path"] = "./"

    return sim_parameters

#############################################################
#############################################################
#############################################################


def create_crop_parameters(mgt_row):

    """ Creates a crop simulation object based on information of the Agmip mgt file. """

    crop_species = "SW"
    crop_name = "wheat"
    crop_variety = "spring-wheat"

    workstep_list = []
    workstep_list.append({"date": get_monica_date_string(mgt_row["sowDay"]),
                          "type": "Sowing",
                          "crop": ["ref", "crops", crop_species]
                          })

    # fertilization steps -------------------------
    fertilizer_map = {
        "Urea-N": "monica_simulation_setup/monica_parameters/mineral-fertilisers/U.json",
        "NH4-N": "monica_simulation_setup/monica_parameters/mineral-fertilisers/AN.json"
    }

    number_of_fertilizer_applications = int(mgt_row["number_fertilizer_application"])
    for fert_application in range(1, number_of_fertilizer_applications + 1):
        date = get_monica_date_string(mgt_row["Fertilizer_date_" + str(fert_application)])
        dose = float(mgt_row["Fertilizer_amount_" + str(fert_application)])
        fertiliser_type = mgt_row["Fertilizer_type_"  + str(fert_application)]

        fertiliser_step = {
            "date": date,
            "type": "MineralFertilization",
            "amount": [dose, "kg N"],
            "partition": ["include-from-file", fertilizer_map[fertiliser_type]]
        }
        workstep_list.append(fertiliser_step)

    harvest_date = mgt_row["Harvest"]
    m_harvest_date = get_monica_date_string(harvest_date)

    print(harvest_date)
    # harvest step -------------------------------
    harvest_step = {
        "type": "Harvest",
        "date": m_harvest_date,
        "percentage": 0.8
    }
    workstep_list.append(harvest_step)

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

########################################################
#############################################################
#############################################################


if __name__ == "__main__":
    generate_sim_and_crop_files()

