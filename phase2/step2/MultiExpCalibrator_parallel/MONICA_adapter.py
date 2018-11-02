import json
import sys
import monica_io
import zmq
import csv
import os
from datetime import date
import collections
import threading
from threading import Thread
from collections import defaultdict
from copy import deepcopy


class monica_adapter(object):
    def __init__(self, exp_maps, obslist):

        #for multi-experiment: create a M-2 relationship between exp_IDs and param files
        self.IDs_paramspaths = {}
        for exp_map in exp_maps:
            self.IDs_paramspaths[exp_map["exp_ID"]] = {}
            self.IDs_paramspaths[exp_map["exp_ID"]]["species"] = exp_map["species_file"]
            self.IDs_paramspaths[exp_map["exp_ID"]]["cultivar"] = exp_map["cultivar_file"]

        #custom events (for MONICA output)
        custom_events = defaultdict(list)
        with open("template_events.json") as _:
            template_events = json.load(_)

        #observations data structures
        self.observations = [] #for spotpy
        for record in obslist:
            my_event = deepcopy(template_events[record["stage"]]) #deepcopy just to be sure :)
            if record["stage"] == "Zadok12":
                #special case, "Stage" (=2) instead of "DOY" is used
                self.observations.append(2)
                my_event[0] = unicode(record["date"].isoformat())
            else:
                self.observations.append(record["DOY"])
            custom_events[record["exp_ID"]].append(my_event[0])
            custom_events[record["exp_ID"]].append(my_event[1])           

        self.species_params={} #map to store different species params sets avoiding repetition
        self.cultivar_params={} #map to store different cultivar params sets avoiding repetition

        #create envs
        self.envs = []
        for exp_map in exp_maps:
            with open(exp_map["sim_file"]) as simfile:
                sim = json.load(simfile)
                #sim["events"] = custom_events[exp_map["exp_ID"]] #customize output, if here monica.io will ignore it (why?)
                #with open("test_sim_events.json", "w") as out_f:
                #    json.dump(sim, out_f, indent=4)
                sim["crop.json"] = exp_map["crop_file"]
                sim["site.json"] = exp_map["site_file"]
                #sim["climate.csv"] = exp_map["climate_file"]

            with open(exp_map["site_file"]) as sitefile:
                site = json.load(sitefile)

            with open(exp_map["crop_file"]) as cropfile:
                crop = json.load(cropfile)
                mycrop = exp_map["crop_ID"]
                crop["crops"][mycrop]["cropParams"]["species"][1] = exp_map["species_file"]
                crop["crops"][mycrop]["cropParams"]["cultivar"][1] = exp_map["cultivar_file"]

            env = monica_io.create_env_json_from_json_config({
                "crop": crop,
                "site": site,
                "sim": sim,
                "climate": ""
            })

            env["events"] = custom_events[exp_map["exp_ID"]] #customize output
            
            #climate is read by the server
            env["csvViaHeaderOptions"] = sim["climate.csv-options"]
            env["csvViaHeaderOptions"]["start-date"] = sim["climate.csv-options"]["start-date"]
            env["csvViaHeaderOptions"]["end-date"] = sim["climate.csv-options"]["end-date"]
            env["pathToClimateCSV"] = []
            env["pathToClimateCSV"].append(exp_map["climate_file"])

            position = int(exp_map["where_in_rotation"][0])

            for position in exp_map["where_in_rotation"]:
                for ws in env["cropRotation"][position]["worksteps"]:
                    if ws["type"] == "Seed" or ws["type"] == "Sowing":
                        self.species_params[exp_map["species_file"]] = ws["crop"]["cropParams"]["species"]
                        self.cultivar_params[exp_map["cultivar_file"]] = ws["crop"]["cropParams"]["cultivar"]
                        break

            #monica_io.add_climate_data_to_env(env, sim) this does not work anymore properly
            
            env["customId"] = exp_map["exp_ID"]
            env["where_in_rotation"] = exp_map["where_in_rotation"]
            self.envs.append(env)

        self.context = zmq.Context()
        self.socket_producer = self.context.socket(zmq.PUSH)
        #self.socket_producer.connect("tcp://cluster2:6666")
        self.socket_producer.connect("tcp://localhost:6666")

    def run(self,args):
        return self._run(*args)

    def _run(self,vector, user_params):

        evallist = []
        self.out = {}

        def seek_set_param(par, p_value, model_params):
            p_name = par["name"]
            array = par["array"]
            add_index = False
            if isinstance(model_params[p_name], int) or isinstance(model_params[p_name], float):
                add_index = False
            elif len(model_params[p_name]) > 1 and isinstance(model_params[p_name][1], basestring):
                add_index = True #the param contains text (e.g., units)
            if array.upper() == "FALSE":
                if add_index:
                    model_params[p_name][0] = p_value
                else:
                    model_params[p_name] = p_value
            else: #param is in an array (possibly nested)
                array = array.split("_") #nested array
                if add_index:
                    array = [0] + array
                if len(array) == 1:
                    model_params[p_name][int(array[0])] = p_value
                elif len(array) == 2:
                    model_params[p_name][int(array[0])][int(array[1])] = p_value
                elif len(array) == 3:
                    model_params[p_name][int(array[0])][int(array[1])][int(array[2])] = p_value
                else:
                    print "param array too nested, contact developers"
            

        #set params according to spotpy sampling. Update all the species/cultivar available
        for i in range(len(user_params)):                        #loop on the user params
            for s in self.species_params:               #loop on the species
                if user_params[i]["name"] in self.species_params[s]:
                    seek_set_param(user_params[i],
                    user_params[i]["derive_function"](vector, self.species_params[s]) if "derive_function" in user_params[i] else vector[i],
                    self.species_params[s])
                else:
                    break                                   #break loop on species if the param is not there
            for cv in self.cultivar_params:                 #loop on the cultivars
                if user_params[i]["name"] in self.cultivar_params[cv]:
                    seek_set_param(user_params[i],
                    user_params[i]["derive_function"](vector, self.cultivar_params[cv]) if "derive_function" in user_params[i] else vector[i],
                    self.cultivar_params[cv])
                else:
                    break
        
        #customize events to get the desired output (DOY Zadok30 and Zadok65, AgMIP-calibration speciic)
        cv_key = self.cultivar_params.keys()[0]
        TSUMS_cv = self.cultivar_params[cv_key]["StageTemperatureSum"][0]
        dr2_Z30 = TSUMS_cv[2] * 0.25

        em2_Z30 = TSUMS_cv[1] + dr2_Z30 
        em2_Z65 = TSUMS_cv[1] + TSUMS_cv[2] + 0.5 * TSUMS_cv[3]

        for env in self.envs:
            for event in env["events"]:
                if isinstance(event,dict) and "Z30" in event.keys():
                    event["while"][2] = em2_Z30
                if isinstance(event,dict) and "Z65" in event.keys():
                    event["while"][2] = em2_Z65

        
        #launch parallel thread for the collector
        collector = Thread(target=self.collect_results)
        collector.daemon = True
        collector.start()

        #send jobs to the MONICA server
        for env in self.envs:
            species = self.species_params[self.IDs_paramspaths[env["customId"]]["species"]]
            cultivar = self.cultivar_params[self.IDs_paramspaths[env["customId"]]["cultivar"]]
            for crop_to_cal in env["where_in_rotation"]:
            #if the crop appears more than once in the rotation, the same params will be set
                for ws in env["cropRotation"][int(crop_to_cal)]["worksteps"]:
                    if ws["type"] == "Seed" or ws["type"] == "Sowing":
                        ws["crop"]["cropParams"]["species"] = species
                        ws["crop"]["cropParams"]["cultivar"] = cultivar
                        break

            self.socket_producer.send_json(env)

        #wait until the collector finishes
        collector.join()
        
        #build the evaluation list for spotpy        
        ordered_out = collections.OrderedDict(sorted(self.out.items()))
        for k, v in ordered_out.iteritems():
            for value in v:
                evallist.append(float(value))
           
        return evallist

        
    def collect_results(self):
        socket_collector = self.context.socket(zmq.PULL)
        #socket_collector.connect("tcp://cluster2:7777")
        socket_collector.connect("tcp://localhost:7777")
        received_results = 0
        leave = False
        while not leave:
            try:
                rec_msg = socket_collector.recv_json()
            except:
                continue            
            
            results_rec = []
            for res in rec_msg["data"]:
                try:
                    event_out = res["results"][0][0]
                    if res["outputIds"][0]["displayName"] == "Stage_Z12" and event_out < 2:
                        #avoid delayed emergence
                        event_out = 999
                    results_rec.append(event_out)
                except:
                    #missing data (e.g., no maturity) replaced by 999
                    results_rec.append(999)
                    print("missing data in custom id " + rec_msg["customId"])
            self.out[int(rec_msg["customId"])] = results_rec
            #print (rec_msg["customId"], results_rec)
            received_results += 1
            #print("total received: " + str(received_results))

            if received_results == len(self.envs):
                leave = True
