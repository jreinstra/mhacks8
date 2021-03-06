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

TRANSIT_CATEGORIES = {
    "DRIVING": 0.0,
    "WALKING": 1.0,
    "BICYCLING": 0.7,
    "TRANSIT": 0.4
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
    client = MongoClient()
    db = client.mhacks
    
    result = result_dicts[thread_index]
    
    for i in xrange(0, len(routes_dict['routes'])):
        route = routes_dict["routes"][i]
        sketch_dict = {}
        for step in route["legs"][0]["steps"]:
            calc_sketchiness(
                step["start_location"]["lat"], step["start_location"]["lng"],
                step["end_location"]["lat"], step["end_location"]["lng"],
                TRANSIT_CATEGORIES[step["travel_mode"]], sketch_dict, db
            )
        total_score = 0.0
        for key, val in sketch_dict.items():
            total_score += val
        result[key_prefix + "_" + str(i)] = total_score


# 0.50 miles roughly equals 805 meters
# inputs: start lat/long and end lat/long
def calc_sketchiness(lat1, lon1, lat2, lon2, travel_mode_mult, sketch_dict, db):
    diff_lat = lat2 - lat1
    diff_lon = lon2 - lon1
    
    dist_meters = int(distance(lat1, lon1, lat2, lon2, 'K') * 1000.0)
    
    # check every 0.75 miles (805 * 1.5) = ~1208
    for x in range(0, dist_meters, 1208):
        proportion_done = 1.0 * x / dist_meters
        lat = (proportion_done * diff_lat) + lat1
        lon = (proportion_done * diff_lon) + lon1
        nearby_crimes_score(sketch_dict, lat, lon, travel_mode_mult, db)

    
def nearby_crimes_score(result_dict, lat, lon, travel_mode_mult, db):
    cursor = db.crimedata.find(
       {
         "loc":
           {"$near":
              {
                "$geometry": {"type": "Point", "coordinates": [lat, lon]},
                "$minDistance": 0,
                "$maxDistance": 805
              }
           }
       }
    ).limit(500)
    
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
            
            result_dict[obj_id] = score_decay * travel_mode_mult
    
    
# borrowed from call it magic
def distance(lat1, lon1, lat2, lon2, unit):
    radlat1 = math.pi * lat1 / 180
    radlat2 = math.pi * lat2 / 180
    radlon1 = math.pi * lon1 / 180
    radlon2 = math.pi * lon2 / 180
    
    theta = lon1 - lon2
    radtheta = math.pi * theta / 180
    dist = math.sin(radlat1) * math.sin(radlat2) + math.cos(radlat1) * math.cos(radlat2) * math.cos(radtheta)
    dist = math.acos(dist)
    dist = dist * 180 / math.pi
    dist = dist * 60 * 1.1515
    
    # Convert dist in mi to dist in km
    if (unit == "K"):
        dist = dist * 1.609344
        
    # Convert dist in mi to dist in nautical mi
    if (unit == "N"):
        dist = dist * 0.8684
        
    return dist
