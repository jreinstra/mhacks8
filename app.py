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
    print(responses)


