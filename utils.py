import math

from pymongo import MongoClient

client = MongoClient()
db = client.mhacks


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
    "FORGERY"; 0,
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

# 0.50 miles roughly equals 805 meters
# inputs: start lat/long and end lat/long
def calc_sketchiness(lat1, lon1, lat2, lon2):
    diff_lat = lat2 - lat1
    diff_lon = lon2 - lon1
    
    dist_meters = int(distance(lat1, lon1, lat2, lon2, 'K') * 1000.0)
    
    result = {}
    
    for x in range(0, dist_meters, 805):
        proportion_done = 1.0 * x / dist_meters
        lat = (proportion_done * diff_lat) + lat1
        lon = (proportion_done * diff_lon) + lon1
        count_nearby_crimes(result, lat, lon)
    
    print "distance in meters", dist_meters
    
    
def count_nearby_crimes(result_dict, lat, lon):
    cursor = db.crimedata.find(
       {
         "loc":
           {"near":
              {
                "geometry": {"type": "Point", "coordinates": [lat, lon]},
                "minDistance": 0,
                "maxDistance": 805
              }
           }
       }
    )
    
    for doc in cursor:
        print doc
        
    print "Find danger level at %s, %s" % (lat, lon)
    
    
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

calc_sketchiness(39.0, -79.2, 38.0, -78)