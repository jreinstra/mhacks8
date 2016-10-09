from flask import Flask, request, abort
from flask_pymongo import PyMongo
import grequests
import requests
import json

from utils import generate_sketch_dict


CONFIGURATION_FILENAME = "configuration.json"

GOOGLE_MAPS_BASE_URL = 'https://maps.googleapis.com/maps/api/directions/json'
GOOGLE_MAPS_MODES = ["walking", "bicycling", "transit"]
GOOGLE_MAPS_API_KEY = ''

UBER_BASE_URL = 'https://api.uber.com/v1/'
UBER_API_KEY = ''

BUS_PRICE = 1.50


def getConfigurationVariables():
    with open (CONFIGURATION_FILENAME) as json_data:
        dictionary = json.load(json_data)
        global GOOGLE_MAPS_API_KEY
        global UBER_API_KEY
        global FB_VALIDATION_TOKEN
        global FB_TOKEN
        GOOGLE_MAPS_API_KEY = dictionary['GOOGLE_MAPS_API_KEY']
        UBER_API_KEY = dictionary['UBER_API_KEY']
        FB_VALIDATION_TOKEN = dictionary['FB_VALIDATION_TOKEN']
        FB_TOKEN = dictionary['FB_TOKEN']


app = Flask(__name__)
getConfigurationVariables()
mongo = PyMongo(app)

@app.route('/bot', methods=['POST'])
def tim_the_bot():
    data = request.get_data()
    print data
    for sender, message in messaging_events(data):
        print "Incoming from %s: %s" % (sender, message)
        send_reply(sender, message)
    return '', 200

def messaging_events(payload):

    data = json.loads(payload)
    messaging_event = data["entry"][0]["messaging"]
    for event in messaging_event:
        if "message" in event and "text" in event["message"]:
            yield event["sender"]["id"], event["message"]["text"].encode('unicode_escape')

def send_reply(recipient_id, message):

    params = {
        "access_token": FB_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)


def buildMapsRequest(type, origin_latitude, origin_longitude, destination_latitude, destination_longitude):
    return GOOGLE_MAPS_BASE_URL + \
    '?origin=' + str(origin_latitude) + "," + str(origin_longitude) + \
    "&destination=" + str(destination_latitude) + "," + str(destination_longitude) +\
    "&key=" + GOOGLE_MAPS_API_KEY + \
    '&alternatives=' + 'true' + \
    '&mode=' + type

def urlsForGoogleMaps(origin_latitude, origin_longitude, destination_latitude, destination_longitude):
    list = []
    for m in GOOGLE_MAPS_MODES:
        list.append(buildMapsRequest(m, origin_latitude, origin_longitude, destination_latitude, destination_longitude))
    return list


def getGoogleMapsDataFromServer(origin_latitude, origin_longitude, destination_latitude, destination_longitude):
    urls = urlsForGoogleMaps(origin_latitude, origin_longitude, destination_latitude, destination_longitude)
    rs = (grequests.get(u) for u in urls)
    responses = grequests.map(rs)

    i = 0
    # we need to assume it's in the same order as GOOGLE_MAPS_MODES
    compositeTimes = {}
    compositePrices = {}
    compositeSketch = {}
    for response in responses:
        identifier = GOOGLE_MAPS_MODES[i]
        jsonResponse = json.loads(response.content)
        modeTimeDictionary = getTravelTimeForGoogleMapsJSON(jsonResponse, identifier)
        modePriceDictionary = calculatePriceFromGoogleMapsJSON(jsonResponse, identifier)
       # modeSketchDictionary = generate_sketch_dict(jsonResponse, identifier)
        compositeTimes.update(modeTimeDictionary)
        compositePrices.update(modePriceDictionary)
       # compositeSketch.update(modeSketchDictionary)
        i += 1

    return compositeTimes, compositePrices, compositeSketch


def calculatePriceFromGoogleMapsJSON(json, identifier):
    routes = json['routes']
    i = 0
    priceDictionary = {}
    for routeDictionary in routes:
        totalPrice = 0
        steps = routeDictionary['legs'][0]['steps']
        for step in steps:
            if step['travel_mode'] == 'TRANSIT':
                if 'transit_details' in step:
                    if step['transit_details']['line']['vehicle']['type'] == 'BUS':
                        totalPrice += BUS_PRICE
            key = identifier + "_" + str(i)
            priceDictionary[key] = totalPrice
        i += 1

    return priceDictionary



def getTravelTimeForGoogleMapsJSON (json, identifier):
    timeDictionary = {}
    routes = json['routes']
    i = 0

    for routeDictionary in routes:
        duration = routeDictionary['legs'][0]['duration']['value']
        key = identifier + "_" + str(i)
        i += 1
        timeDictionary[key] = duration

    return timeDictionary

def getUberFareEstimateURL(origin_latitude, origin_longitude, destination_latitude, destination_longitude):
    return UBER_BASE_URL + "estimates/price"'?start_latitude=' + str(origin_latitude) + \
           "&start_longitude=" + str(origin_longitude) + \
           "&end_latitude=" + str(destination_latitude) + \
           "&end_longitude=" + str(destination_longitude) + \
           "&seat_count=1"

def getUberTimeEstimateURL(origin_latitude, origin_longitude):
    return UBER_BASE_URL + "estimates/time"'?start_latitude=' + str(origin_latitude) + \
           "&start_longitude=" + str(origin_longitude)

def getUberData(origin_latitude, origin_longitude, destination_latitude, destination_longitude):
    urls = [getUberFareEstimateURL(origin_latitude, origin_longitude, destination_latitude, destination_longitude), \
            getUberTimeEstimateURL(origin_latitude, origin_longitude)]

    headers = {"Authorization" : "Token " + UBER_API_KEY}
    rs = (grequests.get(u, headers=headers) for u in urls)
    responses = grequests.map(rs)

    fareResponse = json.loads(responses[0].content)
    timeResponse = json.loads(responses[1].content)

    times = getUberTimeEstimates(timeResponse, fareResponse)
    fares = getUberFareEstimates(fareResponse)

    intersectionTuple = filterDictionariesToUseCommonKeys(times, fares)
    times = intersectionTuple[0]
    fares = intersectionTuple[1]

    sketchDictionary = {}
    for key in times:
        sketchDictionary[key] = 1
    return times, fares, sketchDictionary

def getUberTimeEstimates(timeResponseJSON, fareResponseJSON):
    totalTimeEstimateDictionary = {}
    timeArray = timeResponseJSON['times']
    fareArray = fareResponseJSON['prices']

    for timeDictionary in timeArray:
        product_name = timeDictionary['localized_display_name']
        timeEstimate = timeDictionary['estimate']
        totalTimeEstimateDictionary[product_name] = timeEstimate

    for fareDictionary in fareArray:
        product_name = fareDictionary['localized_display_name']

        if product_name in totalTimeEstimateDictionary:
            duration = fareDictionary['duration']
            currentDuration = totalTimeEstimateDictionary[product_name]
            currentDuration += duration
            totalTimeEstimateDictionary[product_name] = currentDuration

    return totalTimeEstimateDictionary

def getUberFareEstimates(fareResponseJSON):
    pricesDictionary = {}
    fareArray = fareResponseJSON['prices']

    for fareDictonary in fareArray:
        product_name = fareDictonary['localized_display_name']
        low_fare = fareDictonary['low_estimate']
        high_fare = fareDictonary['high_estimate']
        average_fare = (float(low_fare) + float(high_fare))/2.0
        pricesDictionary[product_name] = average_fare

    return pricesDictionary


def filterDictionariesToUseCommonKeys(dict1, dict2):
    keys_1 = set(dict1.keys())
    keys_2 = set(dict2.keys())
    intersection = keys_1 & keys_2
    newDict1 = {}
    newDict2  = {}
    for key in intersection:
        newDict1[key] = dict1[key]
        newDict2[key] = dict2[key]
    return newDict1, newDict2

def getScores(origin_latitude, origin_longitude, destination_latitude, destination_longitude):
    google_maps_scores = getGoogleMapsDataFromServer(origin_latitude, origin_longitude, destination_latitude, destination_longitude)
    time_dictionary = google_maps_scores[0]
    cost_dictionary = google_maps_scores[1]
    sketch_dictionary = google_maps_scores[2]

    uber_scores = getUberData(origin_latitude, origin_longitude, destination_latitude, destination_longitude)
    time_dictionary.update(uber_scores[0])
    cost_dictionary.update(uber_scores[1])
    sketch_dictionary.update(uber_scores[2])

    return time_dictionary, cost_dictionary, sketch_dictionary

def rank(array):
    time = array[0]
    cost = array[1]
    sketch = array[2]

    normalizedTime = normalizeDictionary(time)
    normalizedCost = normalizeDictionary(cost)
    normalizedSketch = normalizeDictionary(sketch)

    average = averageDictionaries([normalizedTime, normalizedCost, normalizedSketch])

    sortedList = sorted(average.items(), key=operator.itemgetter(1))

    return sortedList


def normalizeDictionary(dictionary):
    maxValue = float(max(dictionary.values()))
    minValue = float(min(dictionary.values()))

    newDictionary = {}
    for key in dictionary:
        x = dictionary[key]
        newDictionary[key] = 1 - ((maxValue - float(x)) / (maxValue - minValue))

    return newDictionary

#precondition, should all have same keys to work properly
def averageDictionaries(arrayOfDictionaries):
    averagedDictionary = {}
    if (len(arrayOfDictionaries) < 1):
        return arrayOfDictionaries
    else:
        length = float(len(arrayOfDictionaries))
        lengthReciprocal = 1.0/length
        for dictionary in arrayOfDictionaries:
            for key in dictionary:
                if key in averagedDictionary:
                    value = averagedDictionary[key]
                    value += float(dictionary[key]) * lengthReciprocal
                else:
                    value = float(dictionary[key]) * lengthReciprocal
                averagedDictionary[key] = value

    return averagedDictionary

def main():
    scores = getScores(42.330591,-83.038573,42.337697,-83.086810)
    ranked = rank(scores)

main()