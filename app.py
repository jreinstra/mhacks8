from flask import Flask, request, abort, redirect
from pymongo import MongoClient
from wit import Wit
import grequests
import requests
import json

from utils import generate_sketch_dicts
import operator

client = MongoClient()
db = client.mhacks

CONFIGURATION_FILENAME = "configuration.json"

GOOGLE_MAPS_BASE_URL = 'https://maps.googleapis.com/maps/api/directions/json'
GOOGLE_MAPS_MODES = ["walking", "bicycling", "transit"]
GOOGLE_MAPS_API_KEY = ''

UBER_BASE_URL = 'https://api.uber.com/v1/'
UBER_API_KEY = ''

BUS_PRICE = 1.50

LOCAL_LOC = ['home', 'work']

def getConfigurationVariables():
    with open (CONFIGURATION_FILENAME) as json_data:
        dictionary = json.load(json_data)
        global GOOGLE_MAPS_API_KEY
        global UBER_API_KEY
        global FB_VALIDATION_TOKEN
        global FB_TOKEN
        global WIT_TOKEN
        GOOGLE_MAPS_API_KEY = dictionary['GOOGLE_MAPS_API_KEY']
        UBER_API_KEY = dictionary['UBER_API_KEY']
        FB_VALIDATION_TOKEN = dictionary['FB_VALIDATION_TOKEN']
        FB_TOKEN = dictionary['FB_TOKEN']
        WIT_TOKEN = dictionary['WIT_TOKEN']


app = Flask(__name__)
getConfigurationVariables()

client = Wit(access_token=WIT_TOKEN)

@app.route('/bot', methods=['POST'])
def tim_the_bot():
    if request.method == 'POST':
        # return '',200
        payload = json.loads(request.get_data())
        print(payload)
        for event in payload['entry']:
            messaging = event['messaging']
            for x in messaging:
                if x.get('message') and x['message'].get('text'):
                    message = x['message']['text']
                    recipient_id = x['sender']['id']
                    print "Incoming from %s: %s" % (recipient_id, message)

                    current_user = fetch_user(recipient_id)

                    waiting = current_user.get('waiting', False)

                    if (waiting):
                        waiting_type = current_user['waitingFor']
                        lat,lng = geocode(message)
                        db.user.update({'fbid': recipient_id}, {'$set': {'waiting': False, waiting_type: {'lat': lat, 'lng': lng}}})
                        wit_process_message(recipient_id, get_past_req(recipient_id))
                    else:
                        wit_process_message(recipient_id, message)
                elif x.get('message') and x['message'].get('attachments'):
                    if x['message']['attachments'][0].get('type') == 'location':
                        recipient_id = x['sender']['id']
                        user_lat = x['message']['attachments'][0]['payload']['coordinates']['lat']
                        user_lon = x['message']['attachments'][0]['payload']['coordinates']['long']
                        store_current_loc(recipient_id, user_lat, user_lon)
                        wit_process_message(recipient_id, get_past_req(recipient_id))

    return '', 200


def fetch_user(fbid):
    newUser = {"fbid": fbid, "first_name": fb_get_user(fbid).get('first_name', 'Human')}
    tehuser = db.user.find_one({"fbid": fbid})

    if (tehuser):
        print('[FETCH USER] tehuser: %s' % str(tehuser))
        return tehuser
    else:
        result = db.user.insert_one(newUser)
        print('[FETCH USER] result: %s' % str(result))
        return db.user.find_one({"fbid": fbid})

def fb_send_reply(recipient_id, message):
    params = {"access_token": FB_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": recipient_id}, "message": {"text": message}})

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)

def fb_send_map_reply(recipient_id, message):
    params = {"access_token": FB_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": recipient_id}, "message": {"text": message, "attachment":{"type":"image", "payload":{"url":"https://petersapparel.com/img/shirt.png"}
    , "buttons":[
      {
        "type":"web_url",
        "url":"https://petersfancyapparel.com/classic_white_tshirt",
        "title":"View Item",
        "webview_height_ratio": "compact"
      }
    ]}}})

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)

def fb_get_user(user_id):
    url = "https://graph.facebook.com/v2.6/%s?fields=first_name&access_token=%s" % (user_id, FB_TOKEN)
    r = requests.get(url)
    return r.json()

def fb_request_location(user_id, first_name):
    req_loc_text = "On it %s, all I need is your current location to give you the best and safest routing:" % first_name
    params = {"access_token": FB_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": user_id}, "message": {"text": req_loc_text, "quick_replies":[{"content_type":"location"}]}})

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)


def wit_process_message(recipient_id, message):
    resp = client.message(message)

    intent = None
    intent_array = resp['entities'].get('intent', False)
    if intent_array:
        intent = intent_array[0]['value']
        current_user = fetch_user(recipient_id)
        # fb_request_location(recipient_id, first_name)
        # # fb_send_reply(recipient_id, "Okay %s, let me check that for you, give me on sec." % first_name)

    if intent == 'destination':
        if 'current_location' in current_user:
            query_array = resp['entities'].get('local_search_query', False)
            if query_array:
                query = query_array[0]['value']
                query = query.lower()
                start_lat = current_user['current_location']['lat']
                start_lng = current_user['current_location']['lng']
                first_name = current_user['first_name']
                if query in LOCAL_LOC:
                    if query in current_user:
                        end_lat = current_user[query]['lat']
                        end_lng = current_user[query]['lng']
                        fb_send_reply(recipient_id, "Calculating the safest and fastest route to %s" % query)
                        fb_show_typing(recipient_id)

                        scores_response = getScores(start_lat, start_lng, end_lat, end_lng)
                        scores = scores_response['scores']
                        gmaps = scores_response['gmaps']

                        ranked = rank(scores)

                        key_of_first = ranked[0][0]
                        separatorIndex = key_of_first.index('_')
                        transitMode = key_of_first[:separatorIndex]
                        indexInGmaps = key_of_first[separatorIndex+1:]
<<<<<<< HEAD
                        summary = gmaps[transitMode][indexInGmaps]['summary']
                        print(summary)
                        fb_send_map_reply(recipient_id, "test")
=======
                        summary = gmaps[transitMode]['routes'][int(indexInGmaps)]['summary']

                        fb_send_reply(recipient_id, str(ranked))
>>>>>>> 18d0e59df8410d5ceef7853be0bbe6b48ea11d18
                        # Tell them to wait, then do the magic
                        # LETS GO FOR IT
                    else:
                        store_past_req(recipient_id, message)
                        store_extra_param(recipient_id, query)
                        fb_send_reply(recipient_id, "Please enter the address for your %s" % query)
                else:
                    poi_loc = findPOI(start_lat, start_lng, query)
                    fb_send_reply(recipient_id, "Found a %s close to you %s. Calculating the safest and fastest route now!" % (poi_loc['name'], first_name))
                    fb_show_typing(recipient_id)

                    scores = getScores(start_lat, start_lng, poi_loc['lat'], poi_loc['lng'])
                    ranked = rank(scores)
                    fb_send_reply(recipient_id, str(ranked))
                    # Tell them to wait, then do the magic
        else:
            store_past_req(recipient_id, message)
            fb_request_location(recipient_id, current_user.get("first_name"))
    elif intent == 'best_transportation':
        return 'You should take the train, really trust me.'
    elif intent == 'hello':
        fb_send_reply(recipient_id, "Hi there!")
    elif intent == 'thanks':
        fb_send_reply(recipient_id, "You are welcome!")
    else:
        return 'Sorry, I was unable to understand you.'

@app.route('/gmaps')
def hello():
    slat = request.args.get('slat')
    slng = request.args.get('slng')
    elat = request.args.get('elat')
    elng = request.args.get('elng')
    type = request.args.get('type')

    main_redirect = "comgooglemaps://?saddr=%s,%s&daddr=%s,%sdirectionsmode=%s" % (slat,slng,elat,elng,type)
    return redirect(main_redirect, code=302)

def store_extra_param(fbid, type):
    db.user.update({'fbid': fbid}, {'$set': {'waiting': True, 'waitingFor': type}})

def fb_show_typing(fbid):
    params = {"access_token": FB_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": fbid}, "sender_action":"typing_on"})

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)

def fb_hide_typing(fbid):
    params = {"access_token": FB_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": fbid}, "sender_action":"typing_off"})

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)

def store_current_loc(fbid, lat, lng):
    db.user.update({'fbid': fbid}, {'$set': {'current_location': {'lat': lat, 'lng': lng}}})

def store_past_req(fbid, req):
    db.user.update({'fbid': fbid}, {'$set': {'last_request': req}})

def get_past_req(fbid):
    current_user = db.user.find_one({'fbid': fbid})
    last_request = current_user.get('last_request', False)
    db.user.update({'fbid': fbid}, {'$set': {'last_request': False}})

    return last_request

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
    
    jsonResponses = []
    cleanedJSONResponses = {}
    identifiers = []
    
    for response in responses:
        identifier = GOOGLE_MAPS_MODES[i]
        jsonResponse = json.loads(response.content)
        cleanedJSONResponses[identifier] = jsonResponse
        modeTimeDictionary = getTravelTimeForGoogleMapsJSON(jsonResponse, identifier)
        modePriceDictionary = calculatePriceFromGoogleMapsJSON(jsonResponse, identifier)
        compositeTimes.update(modeTimeDictionary)
        compositePrices.update(modePriceDictionary)
        
        jsonResponses.append(jsonResponse)
        identifiers.append(identifier)
        i += 1
        
    compositeSketch = generate_sketch_dicts(jsonResponses, identifiers)


    return {"scores" : (compositeTimes, compositePrices, compositeSketch),
            "json" : cleanedJSONResponses}


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
    google_maps_response = getGoogleMapsDataFromServer(origin_latitude, origin_longitude, destination_latitude, destination_longitude)
    google_maps_scores = google_maps_response['scores']

    time_dictionary = google_maps_scores[0]
    cost_dictionary = google_maps_scores[1]
    sketch_dictionary = google_maps_scores[2]

    uber_scores = getUberData(origin_latitude, origin_longitude, destination_latitude, destination_longitude)
    time_dictionary.update(uber_scores[0])
    cost_dictionary.update(uber_scores[1])
    sketch_dictionary.update(uber_scores[2])

    return {"scores" : (time_dictionary, cost_dictionary, sketch_dictionary),
            "gmaps" : google_maps_response['json']}


def rank(array):
    time = array[0]
    cost = array[1]
    sketch = array[2]

    normalizedTime = normalizeDictionary(time)
    normalizedCost = normalizeDictionary(cost)
    normalizedSketch = normalizeDictionary(sketch)

    average = averageDictionaries([(normalizedTime, (1.0/3.0)), (normalizedCost, (1.0/3.0)), (normalizedSketch, (1.0/3.0))])

    sortedList = sorted(average.items(), key=operator.itemgetter(1))

    return sortedList


def normalizeDictionary(dictionary):
    values = dictionary.values()
    maxValue = float(max(values))
    minValue = float(min(values))
    
    if maxValue == minValue:
        return {key:1 for key, value in dictionary.items()}
    else:
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
        for tuple in arrayOfDictionaries:
            dictionary = tuple[0]
            weight = tuple[1]
            for key in dictionary:
                if key in averagedDictionary:
                    value = averagedDictionary[key]
                    value += float(dictionary[key]) * weight
                else:
                    value = float(dictionary[key]) * weight
                averagedDictionary[key] = value

    return averagedDictionary


def geocode(address):
    url = 'https://maps.googleapis.com/maps/api/geocode/json?key=' + GOOGLE_MAPS_API_KEY + '&address=' + address
    request = requests.get(url)
    location = request.json()['results'][0]['geometry']['location']
    lat = location['lat']
    lng = location['lng']
    return lat, lng

def findPOI(lat, lng, poiName):
    url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?key=' + GOOGLE_MAPS_API_KEY + \
          "&location=" + str(lat) + "," + str(lng) + \
          "&rankby=distance"
    request = requests.get(url)
    results = request.json()['results']
    if len(results) > 0:
        firstLocation = results[0]
        lat = firstLocation['geometry']['location']['lat']
        lng = firstLocation['geometry']['location']['lng']
        return {
            'name' : firstLocation['name'],
            'lat' : lat,
            'lng' : lng
        }
    return None



# def main():
#     # scores = getScores(42.330591,-83.038573,42.337697,-83.086810)
#     # ranked = rank(scores)
#     # print ranked
#
# main()