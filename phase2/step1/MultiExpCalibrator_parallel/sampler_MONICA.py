from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import os
import spotpy
import spotpy_setup_MONICA
import csv
from datetime import date
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from collections import defaultdict

font = {'family' : 'calibri',
    'weight' : 'normal',
    'size'   : 18}

def make_lambda(excel):
    return lambda v, p: eval(excel)

def produce_plot(experiments, variable, ylabel='Best model simulation', xlabel='Date'):    
    #cnames = list(colors.cnames)

    plt.rc('font', **font)
    colors = ['grey', 'black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue']
    n_subplots = max(2, len(experiments))
    # N subplots, sharing x axis
    width = 20
    height = n_subplots * 10
    f, axarr = plt.subplots(n_subplots, sharex=False, figsize=(width, height))
    i=0
    #find min and max coords
    xy_min = 999
    xy_max = 0
    for exp in experiments:
        xy_min = min(xy_min, min(experiments[exp]["obs"]), min(experiments[exp]["sims"]))
        xy_max = max(xy_max, max(experiments[exp]["obs"]), max(experiments[exp]["sims"]))
    
    xy_min -= 10
    xy_max += 10

    for exp in experiments:
        RMSE = spotpy.objectivefunctions.rmse(experiments[exp]["obs"], experiments[exp]["sims"])
        axarr[i].plot(experiments[exp]["obs"], experiments[exp]["sims"], 'ro', markersize=8, label='obs vs sims  - exp ' + exp + ': RMSE=' + str(round(RMSE, 3)))
        axarr[i].plot([xy_min, xy_max], [xy_min, xy_max],'-', color=colors[7], linewidth=2)
        axarr[i].legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2, mode="expand", borderaxespad=0.)
        #axarr[i].set_title(str(exp))
        i +=1
    filename = variable + '.png'
    f.savefig(filename)
    text = 'A figure has been saved as ' + filename
    print(text)

cultivar = "bermude"#"apache" #"bermude"
if cultivar == "apache":
    crop_sim_site_MAP = "crop_sim_site_MAP_apache.csv"
    observations = "observations_apache.csv"
elif cultivar == "bermude":
    crop_sim_site_MAP = "crop_sim_site_MAP_bermude.csv"
    observations = "observations_bermude.csv"

#read general settings
exp_maps = []
basepath = os.path.dirname(os.path.abspath(__file__))
with open(crop_sim_site_MAP) as exp_mapfile:
    dialect = csv.Sniffer().sniff(exp_mapfile.read(), delimiters=';,\t')
    exp_mapfile.seek(0)
    reader = csv.reader(exp_mapfile, dialect)
    next(reader, None)  # skip the header
    for row in reader:
        exp_map = {}
        exp_map["exp_ID"] = row[0]
        exp_map["sim_file"] = basepath+"\\sim_files\\"+row[1]
        exp_map["crop_file"] = basepath+"\\crop_files\\"+row[2]
        exp_map["site_file"] = basepath+"\\site_files\\"+row[3]
        exp_map["climate_file"] = basepath+"\\climate_files\\"+row[4]
        exp_map["species_file"] = basepath+"\\param_files\\"+row[5]
        exp_map["cultivar_file"] = basepath+"\\param_files\\"+row[6]
        exp_map["where_in_rotation"] = [int(x) for x in row[7].split("-")]
        exp_map["crop_ID"] = row[8]
        exp_maps.append(exp_map)

#read observations
obslist = [] #for envs (outputs)
with open(observations) as obsfile:
    dialect = csv.Sniffer().sniff(obsfile.read(), delimiters=';,\t')
    obsfile.seek(0)
    reader = csv.reader(obsfile, dialect)
    next(reader, None)  # skip the header
    for row in reader:
        if row[4].upper() == "Y":
            record = {}
            record["exp_ID"] = row[0]
            record["value"] = int(row[2])
            obslist.append(record) #TODO:Add weight here?

#order obslist by exp_id to avoid mismatch between observation/evaluation lists
def getKey(record):
    return int(record["exp_ID"])
obslist = sorted(obslist, key=getKey)

#read params to be calibrated
params = []
with open('calibratethese.csv') as paramscsv:
    dialect = csv.Sniffer().sniff(paramscsv.read(), delimiters=';,\t')
    paramscsv.seek(0)
    reader = csv.reader(paramscsv, dialect)
    next(reader, None)  # skip the header
    for row in reader:
        p={}
        p["name"] = row[0]
        p["array"] = row[1]
        p["low"] = row[2]
        p["high"] = row[3]
        p["stepsize"] = row[4]
        p["optguess"] = row[5]
        p["minbound"] = row[6]
        p["maxbound"] = row[7]
        if len(row) == 9 and row[8] != "":
            p["derive_function"] = make_lambda(row[8])
        params.append(p)

spot_setup = spotpy_setup_MONICA.spot_setup(params, exp_maps, obslist)
rep = 50
results = []

sampler = spotpy.algorithms.sceua(spot_setup, dbname='SCEUA', dbformat='ram')
sampler.sample(rep, ngs=len(params)+1, kstop=10)
#sampler.sample(rep, ngs=3, kstop=50, pcento=0.01, peps=0.05)
results.append(sampler.getdata())

best = sampler.status.params

with open('optimizedparams.csv', 'wb') as outcsvfile:
    writer = csv.writer(outcsvfile)        
    for i in range(len(best)):
        outrow=[]
        arr_pos = ""
        if params[i]["array"].upper() != "FALSE":
            arr_pos = params[i]["array"]        
        outrow.append(params[i]["name"]+arr_pos)
        outrow.append(best[i])
        writer.writerow(outrow)
    if len(params) > len(best):
        reminder = []
        reminder.append("Don't forget to calculate and set derived params!")
        writer.writerow(reminder)
    text='optimized parameters saved!'
    print(text)

#PLOTTING
#get the best model run
for i in range(len(results)):
    index,maximum=spotpy.analyser.get_maxlikeindex(results[i])

bestmodelrun=list(spotpy.analyser.get_modelruns(results[i])[index][0]) #Transform values into list to ensure plotting

#retrieve info for plots
print("preparing charts...")

all_exps = defaultdict(lambda: defaultdict(list))

for i in range(len(obslist)):
    expID = obslist[i]["exp_ID"]
    all_exps[expID]["obs"].append(obslist[i]["value"])
    all_exps[expID]["sims"].append(bestmodelrun[i])

produce_plot(all_exps, "BBCHdoys")

print("finished!")



