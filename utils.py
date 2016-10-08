import math

# 0.50 miles roughly equals 805
# inputs: start lat/long and end lat/long
def calc_sketchiness(lat1, lon1, lat2, lon2):
    diff_lat = lat2 - lat1
    diff_lon = lon2 - lon1
    
    dist_meters = int(distance(lat1, lon1, lat2, lon2, 'K') * 1000.0)
    
    for x in range(0, dist_meters, 805):
        proportion_done = 1.0 * x / dist_meters
        lat = (proportion_done * diff_lat) + lat1
        lon = (proportion_done * diff_lon) + lon1
        print "Find danger level at %s, %s" % (lat, lon)
    
    print "distance in meters", dist_meters
    
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