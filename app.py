from flask import Flask
from flask_pymongo import PyMongo
import grequests
import json


CONFIGURATION_FILENAME = "configuration.json"

GOOGLE_MAPS_BASE_URL = 'https://maps.googleapis.com/maps/api/directions/json'
GOOGLE_MAPS_MODES = ["walking", "bicycling", "transit"]
GOOGLE_MAPS_API_KEY = ''

UBER_BASE_URL = 'https://api.uber.com/v1/'
UBER_API_KEY = ''


def getConfigurationVariables():
    with open (CONFIGURATION_FILENAME) as json_data:
        dictionary = json.load(json_data)
        global GOOGLE_MAPS_API_KEY
        global UBER_API_KEY
        GOOGLE_MAPS_API_KEY = dictionary['GOOGLE_MAPS_API_KEY']
        UBER_API_KEY = dictionary['UBER_API_KEY']


app = Flask(__name__)
getConfigurationVariables()
mongo = PyMongo(app)


def buildMapsRequest(type, origin_latitude, origin_longitude, destination_latitude, destination_longitude):
    return GOOGLE_MAPS_BASE_URL + \
    '?origin=' + origin_latitude + "," + destination_longitude + \
    "&destination=" + destination_latitude + "," + destination_longitude +\
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
    responses = grequests.imap(rs)


def getUberFareEstimateURL(origin_latitude, origin_longitude, destination_latitude, destination_longitude):
    return UBER_BASE_URL + "estimates/price"'?start_latitude=' + origin_latitude + \
           "&start_longitude=" + origin_longitude + \
           "&end_latitude=" + destination_latitude + \
           "&end_longitude=" + destination_longitude + \
           "&seat_count=1"

def getUberTimeEstimateURL(origin_latitude, origin_longitude):
    return UBER_BASE_URL + "estimates/time"'?start_latitude=' + origin_latitude + \
           "&start_longitude=" + origin_longitude

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



getUberData('37.437007', '-122.142686', '37.453263', '-122.191283')
