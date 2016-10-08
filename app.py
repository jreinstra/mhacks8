from flask import Flask
from flask_pymongo import PyMongo
import grequests
import json

CONFIGURATION_FILENAME = "configuration.json"

GOOGLE_MAPS_BASE_URL = 'https://maps.googleapis.com/maps/api/directions/json'
GOOGLE_MAPS_MODES = ["driving", "walking", "bicycling", "transit"]
GOOGLE_MAPS_API_KEY = ''


def getConfigurationVariables():
    with open (CONFIGURATION_FILENAME) as json_data:
        dictionary = json.load(json_data)
        GOOGLE_MAPS_API_KEY = dictionary['GOOGLE_MAPS_API_KEY']




#app = Flask(__name__)
getConfigurationVariables()
#mongo = PyMongo(app)


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







