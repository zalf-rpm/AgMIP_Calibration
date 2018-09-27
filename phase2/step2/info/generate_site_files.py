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
from xlrd import open_workbook
import re


column_index = {
    'depth': 1,
    'bd': 2,
    'pwp': 3,
    'fc': 4,
    'sat': 5,
    'c_org': 7,
    'ph': 8,
    'clay': 9,
    'silt': 10,
    'sand': 11,
    'init': 12
}

#############################################################
#############################################################
#############################################################


def generate_monica_site_files():

    output_dir = "sim_files/"



    sites_config = {
        "bungunya":     {"years": [2012],               "rows": [6, 12],    "latitude": '-28.43'},
        "corrigin":     {"years": [2010, 2011, 2012],   "rows": [20, 24],   "latitude": '-32.33'},
        "eradu":        {"years": [2010, 2011, 2012],   "rows": [32, 38],   "latitude": '-28.69'},
        "lake_bolac":   {"years": [2010, 2011],         "rows": [51, 57],   "latitude": '-37.71'},
        "minnipa":      {"years": [2010, 2011, 2012],   "rows": [65, 69],   "latitude": '-32.84'},
        "nangwee":      {"years": [2012],               "rows": [77, 83],   "latitude": '-27.66'},
        "spring_ridge": {"years": [2010, 2011],         "rows": [91, 96],   "latitude": '-31.39'},
        "temora":       {"years": [2011, 2012],         "rows": [104, 110], "latitude": '-34.41'},
        "turretfield":  {"years": [2011, 2012],         "rows": [118, 122], "latitude": '-34.55'},
        "walpeup":      {"years": [2010, 2011, 2012],   "rows": [130, 136], "latitude": '-35.12'}
    }

    # read in management information
    soil_file = "CSIRO_data_set/19_04_2018  NVT 2010-2012 Soil and Management information.xlsx"
    wb = open_workbook(soil_file)
    soil_sheet = wb.sheet_by_name("Soils")

    # iterate over every row/environment where row contains the setup of one simulation
    for site_name, site_config in sites_config.items():

        site_years = site_config["years"]
        site_rows = site_config["rows"]
        print "-----------------------------------------"
        print "Site: ", site_name, "\tYears: ", site_years, "\tRows: ", site_rows

        for year_index, year in enumerate(site_years):
            print( "-------------------------\n", site_name, "\t", year,)

            site = {}
            site_parameters = {
                "Latitude": float(site_config['latitude']),
                "Slope": 0.01,  # ???
                "HeightNN": [0.0],
                "NDeposition": [30, "kg N ha-1 y-1"]
            }

            # Soil Parameters per Horizon
            number_of_horizons = site_rows[1] - site_rows[0] + 1
            print "number of horizons: ", number_of_horizons

            soil_profile_parameter_list = []
            for row in range(site_rows[0]-1,  site_rows[0]-1 + number_of_horizons):
                print "Row:", row, soil_sheet.cell_value(row, column_index['pwp'])
                # calculate horizon depth
                depth = soil_sheet.cell_value(row, column_index['depth'])
                m = re.match(r'(\d+)-(\d+)', depth)
                h_begin = 0.0
                h_end = 0.0
                if m is not None:
                    h_begin =  float(m.group(1))
                    h_end = float(m.group(2))

                pwp = round(float(soil_sheet.cell_value(row, column_index['pwp'])), 3)
                fc = round(float(soil_sheet.cell_value(row, column_index['fc'])), 3)
                bulk_density = round(float(soil_sheet.cell_value(row, column_index['bd'])) * 1000.0, 2)
                # set up other parameters
                soil_profile_parameter = {
                    "Thickness": [h_end-h_begin, "cm"],
                    "Sceleton": 0.0,
                    "Sand": round(float(soil_sheet.cell_value(row, column_index['sand']))/100.0, 3),
                    "Clay": round(float(soil_sheet.cell_value(row, column_index['clay']))/100.0, 3),
                    "Silt": round(float(soil_sheet.cell_value(row, column_index['silt'])) / 100.0, 3),
                    "PermanentWiltingPoint": pwp,
                    "FieldCapacity": fc,
                    "SoilOrganicCarbon": round(float(soil_sheet.cell_value(row, column_index['c_org'])) * 100.0, 2),
                    "SoilBulkDensity": bulk_density,
                    "pH": round(float(soil_sheet.cell_value(row, column_index['ph'])), 3)
                }

                # initialisation
                col_init = column_index['init'] + (year_index * 2)
                print "Col", col_init, "\trow", row, "\tValue:", soil_sheet.cell_value(row, col_init)
                initial_water = round(float(soil_sheet.cell_value(row, col_init)), 3)

                initial_soil_nitrate = round(float(soil_sheet.cell_value(row, col_init + 1)), 3)  # [ppm]
                initial_soil_nitrate = (initial_soil_nitrate * bulk_density) / 1000.0       # [kg NO3-N m-3]

                print "Initial water: ", initial_water, "\tNitrate conc: ", initial_soil_nitrate
                soil_profile_parameter["SoilMoisturePercentFC"] = round((initial_water / fc) * 100.0, 2)
                soil_profile_parameter["SoilNitrate"] = round(initial_soil_nitrate, 2)



                soil_profile_parameter_list.append(soil_profile_parameter)

            site_parameters["SoilProfileParameters"] = soil_profile_parameter_list
            site["SiteParameters"] = site_parameters

            # additional MONICA parameters
            site["SoilTemperatureParameters"] = ["include-from-file",
                                                 "monica_simulation_setup/monica_parameters/general/soil-temperature.json"]
            site["EnvironmentParameters"] = {
                "=": ["include-from-file", "monica_simulation_setup/monica_parameters/general/environment.json"],
                "LeachingDepth": 2.0,
                "WindSpeedHeight": 2.5,
                "AtmosphericCO2": 395
            }
            site["SoilOrganicParameters"] = ["include-from-file",
                                             "monica_simulation_setup/monica_parameters/general/soil-organic.json"]
            site["SoilTransportParameters"] = ["include-from-file",
                                               "monica_simulation_setup/monica_parameters/general/soil-transport.json"]
            site["SoilMoistureParameters"] = ["include-from-file",
                                              "monica_simulation_setup/monica_parameters/general/soil-moisture.json"]

            with open(output_dir + "site-" + site_name + "-" + str(year) + ".json", "w") as fp:
                json.dump(site, fp=fp, indent=4)


#############################################################
#############################################################
#############################################################

########################################################
#############################################################
#############################################################


if __name__ == "__main__":
    generate_monica_site_files()

