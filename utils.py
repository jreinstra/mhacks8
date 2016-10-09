import math

from datetime import datetime
from pymongo import MongoClient
from threading import Thread


CRIME_CATEGORIES = {
    "MISCELLANEOUS": 1,
    "LARCENY": 3,
    "FRAUD": 0,
    "DAMAGE TO PROPERTY": 4,
    "ASSAULT": 5,
    "MURDER/INFORMATION": 6,
    "AGGRAVATED ASSAULT": 6,
    "WEAPONS OFFENSES": 2,
    "BURGLARY": 4,
    "STOLEN VEHICLE": 4,
    "DANGEROUS DRUGS": 2,
    "ESCAPE": 5,
    "OBSTRUCTING THE POLICE": 2,
    "OBSTRUCTING JUDICIARY": 1,
    "ROBBERY": 4,
    "EXTORTION": 5,
    "HOMICIDE": 10,
    "OUIL": 3,
    "TRAFFIC": 1,
    "DISORDERLY CONDUCT": 1,
    "ARSON": 4,
    "STOLEN PROPERTY": 3,
    "OTHER BURGLARY": 3,
    "EMBEZZLEMENT": 0,
    "FAMILY OFFENSE": 1,
    "KIDNAPING": 8,
    "FORGERY": 0,
    "SOLICITATION": 1,
    "OTHER": 1,
    "IMMIGRATION": 1,
    "VAGRANCY (OTHER)": 1,
    "CIVIL": 0,
    "LIQUOR": 0,
    "RUNAWAY": 2,
    "ENVIRONMENT": 0,
    "JUSTIFIABLE HOMICIDE": 5,
    "OBSCENITY": 0,
    "TRAFFIC OFFENSES": 0,
    "NEGLIGENT HOMICIDE": 4,
    "MISCELLANEOUS ARREST": 1,
    "GAMBLING": 0,
    "BRIBERY": 0,
    "DRUNKENNESS": 1,
    "MILITARY": 0,
    "ABORTION": 1,
    "KIDNAPPING": 8
}


def generate_sketch_dicts(routes_dicts, key_prefixes):
    N = len(routes_dicts)
    result_dicts = [{}] * N
    
    threads = []
    for i in xrange(0, N):
        t = Thread(target=generate_sketch_dict, args=(routes_dicts[i], key_prefixes[i], result_dicts, i))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    result = {}
    for result_dict in result_dicts:
        result.update(result_dict)
    return result


def generate_sketch_dict(routes_dict, key_prefix, result_dicts, thread_index):
    print "%s: creating client..." % thread_index
    client = MongoClient()
    db = client.mhacks
    print "%s: client loaded" % thread_index
    
    result = result_dicts[thread_index]
    
    for i in xrange(0, len(routes_dict['routes'])):
        print "%s: loading route %s..." % (thread_index, i)
        route = routes_dict["routes"][i]
        sketch_dict = {}
        coordinates = []
        for step in route["legs"][0]["steps"]:
            coordinates.append(
                [
                    [step["start_location"]["lat"], step["start_location"]["lng"]],
                    [step["end_location"]["lat"], step["end_location"]["lng"]]
                ]
            )
            
        nearby_crimes_score(sketch_dict, coordinates, db)
        total_score = 0.0
        for key, val in sketch_dict.items():
            total_score += val
        result[key_prefix + str(i)] = total_score
        print "%s: route %s loaded" % (thread_index, i)

    
def nearby_crimes_score(result_dict, coordinates, db):
    print "\tloading crime data for lat/lon..."
    cursor = db.crimedata.find(
       {
         "loc":
           {"$near":
              {
                "$geometry": {"type": "MultiLineString", "coordinates": coordinates},
                "$minDistance": 0,
                "$maxDistance": 805
              }
           }
       }
    ).limit(500)
    print "\tloaded crime data"
    
    for doc in cursor:
        obj_id = doc["_id"]
        if not obj_id in result_dict:
            crime_date = datetime.strptime(doc["INCIDENTDATE"], '%m/%d/%Y')
            today = datetime.utcnow()
            
            num_days_ago = (today - crime_date).days
            
            # time decay with half life of 6 months
            time_decay = 0.5 ** (num_days_ago / 182.5)
            
            score = CRIME_CATEGORIES[doc["CATEGORY"].split(" - ")[0]]
            score_decay = time_decay * score
            
            result_dict[obj_id] = score_decay
