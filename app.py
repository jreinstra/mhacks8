from flask import Flask
from flask_pymongo import PyMongo
import grequests

app = Flask(__name__)
mongo = PyMongo(app)
