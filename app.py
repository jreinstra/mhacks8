from flask import Flask
from flask_pymongo import PyMongo
import grequests
import json


GOOGLE_MAPS_BASE_URL = 'https://maps.googleapis.com/maps/api/directions/'
GOOGLE_MAPS_API_KEY = ''


def getConfigurationVariables():
    with open ('MHACKS_8_CONFIGURATION.JSON') as json_data:
        dictionary = json.load(json_data)
        GOOGLE_MAPS_BASE_URL = dictionary['GOOGLE_MAPS_API_KEY']



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





