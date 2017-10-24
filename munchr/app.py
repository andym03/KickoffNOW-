#!/usr/bin/python3

import os
from sys import argv, stderr
import pprint

import time

from flask import *
import sqlite3
import re
import json
import operator

#geoip stuff
import geoip2.database
from geoip2.errors import AddressNotFoundError

# Modules stored in current folder
import db

app = Flask(__name__)
portNum = int(argv[1])
if portNum == 443:
    from flask_sslify import SSLify
    SSLify(app)

IMAGE_UPLOAD_FOLDER = '/static/user-uploads/'
ALLOWED_IMAGE_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
app.config['UPLOAD_FOLDER'] = IMAGE_UPLOAD_FOLDER

def get_db():
    global g
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("database.db")
        db.row_factory = sqlite3.Row
    return db

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/desktop/', methods=['GET', 'POST'])
def desktop():
    # TODO: ALso fetch foods form database, sort by date added and display recently added foods at top
    # of the page
    conn = get_db()
    restaurants = db.getPopularRestaurants(conn)
    albums = db.getAllAlbums(conn)
    for album in albums:
        album["images"] = json.loads(album["imagesJSON"])
        album["restaurantName"] = ((conn.execute("SELECT name FROM restaurants WHERE ID = ?", (album["restaurant"],))).fetchone())[0]
        album["restaurantID"] = album["restaurant"]
    albums=list(reversed(sorted(albums, key=lambda k: k['addedTimestamp'])))
    return render_template('home.html', restaurants=restaurants, albums=albums[:12])

@app.route('/search', methods=['GET', 'POST'])
def searchResults():
    query = request.values.get("query")
    search_param = request.values.get("search_param")
    conn = get_db()
    results = []
    if search_param == 'restaurant':
        results = db.searchRestaurant(conn.cursor(), query)
        return render_template('searchResults.html', restaurants=results, query=query, count=len(results))

    elif search_param == 'categories':
        # should be for restaurant categories as well, right now just album categories
        results = db.searchAlbum(conn.cursor(), query)
        if results:
            for album in results:
                album["images"] = json.loads(album["imagesJSON"])
        return render_template('searchResults.html', albums=results, query=query, count=len(results))
    elif search_param == 'food':
        results = db.searchAlbumName(conn.cursor(), query)
        if results:
            for album in results:
                album["images"] = json.loads(album["imagesJSON"])
        return render_template('searchResults.html', albums=results, query=query, count=len(results))
    elif search_param == 'all':
        restaurants = db.searchRestaurant(conn.cursor(), query)
        albums = db.searchAlbumAll(conn.cursor(), query)
        if albums:
            for album in albums:
                album["images"] = json.loads(album["imagesJSON"])
        return render_template('searchResults.html', albums=albums, restaurants=restaurants, query=query, count=len(albums) + len(restaurants))

    # TODO TODO Implement handling for search_param = "categories" or "food"
    return render_template('searchResults.html', results=results, query=query, count=len(results))


@app.route('/')
def rootRedirect():
    return redirect('/desktop/')

@app.route('/foods/')
def foodsPage():

    conn = get_db()
    cursor = conn.cursor()

    conn.commit()
    cursor.execute("SELECT * FROM album ORDER BY categories asc")
    albums = db.getAllAlbums(conn)
    restaurants = db.restaurantsToListOfDicts(conn)
    restaurants = query_db("SELECT * FROM restaurants ORDER BY categories asc")
    #restaurants = query_db("SELECT * FROM restaurants")
    albums = query_db("SELECT * FROM album ORDER BY categories asc")
    return render_template('foods-page.html', foods=albums, restaurant=restaurants)

# Endpoint for ajax requests that want a JSON object with the specified
# data. E.g. a list of categories or restaurant names with ID's
@app.route('/fetch-data/<data>')
def fetchData(data):
    conn = get_db()
    if data == "categories":
        return json.dumps(db.categoriesToList(conn))
    elif data == "restaurants":
        return json.dumps(db.restaurantNamesToList(conn))
    else:
        return "UNKNOWN DATATYPE"
    conn.commit()
    conn.close()

@app.route('/add-food/', methods=['GET', 'POST'])
def addFood():
    conn = get_db()

    print("Request.files:")
    pprint.pprint(request.files)

    restaurantName = ""
    if request.values.get("restaurantID"):
        restaurantName = db.restaurantNameFromID(request.values.get("restaurantID"), conn)

    print("add food requested. request values:")
    print(request.values)

    print(json.dumps(db.restaurantNamesToList(conn)))

    if request.values.get("name"):
        newAlbum = {key : request.values.get(key) for key in ['name', 'categories', 'imageURL']}

        username = request.values.get("username");
        if username == None or username == "Login":
            return "We had a problem getting your name from your submission. Try again: <a href='/add-food/'>add food</a>."

        # We need to turn the restaurant name into the actual ID.
        restaurantID = db.getRestaurantID(request.values.get("restaurant"), conn)
        print("Restaurant: {}, ID: {}".format(request.values.get("restaurant"), restaurantID))
        if restaurantID == None:
            return "Invalid restaurant name entered. Try again <a href='/add-food/'>add food</a>"
        else:
            newAlbum['restaurant'] = restaurantID

        # Handle imageURL separately. user may have either entered a URL, or chosen
        # to upload an image. For the latter case we must first process the upload, then
        # generate the URL from where we stored the image, and then append to the dict
        # to pass to db.py

        hasFile = True
        if 'file' not in request.files:
            hasFile = False
        else:
            file = request.files['file']
            if file.filename != '' and '.' in file.filename and \
                    file.filename.rsplit('.',1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS:
                uploadedFilePath = db.addUploadedImage(file)
            else:
                hasFile = False

        imageURL = request.values.get("imageURL")
        if hasFile:
            newAlbum['imageURL'] = uploadedFilePath
        else:
            if imageURL == None:
                return "Cover Image URL not specified, and no file was uploaded. Try again <a href='/add-food/'>add food</a>"
            else:
                newAlbum['imageURL'] = imageURL


        albumID = db.addAlbum(newAlbum, username, conn)  # conn.commit run inside db.addAlbum()
        return redirect(url_for("showRestaurantMenu", restaurantID=restaurantID, albumID=albumID))
    else:
        return render_template('add-food.html', name=restaurantName, restaurants=json.dumps(db.restaurantNamesToList(conn)), categories=json.dumps(db.categoriesToList(conn)))

@app.route('/add-restaurant/', methods=['GET', 'POST'])
def addRestaurant():
    print("add restaurant requested. request values:")
    print(request.values)

    conn = get_db()
    if request.values.get("name"):
        restObj = {key : request.values.get(key) for key in ['name', 'address', 'phone', 'imageURL', 'categories', 'coordsX', 'coordsY']}

        if request.values.get("username"):
            restaurantID = db.addRestaurantEntry(restObj, request.values.get("username"), conn)
            if restaurantID:
                return redirect(url_for("restaurantDetails", restaurantID=restaurantID))      # To new restaurant page
            else:
                return redirect("/desktop/")
        else:
            return "We had a problem getting your name from your submission. Try again: <a href='/add-food/'>add food</a>."

    return render_template('add-restaurant.html')

@app.route('/addReview', methods=['POST'])
def addReview():
    """
    Recieves JSON review object from javascript as ajax request.
    """
    conn = get_db()
    print("add review called. data:")
    print(request.data)
    pprint.pprint(request.get_json())

    reviewObj = request.get_json()

    if reviewObj:
        if (not reviewObj.get("username")) or reviewObj.get("username") == "Login":
            return "Unable to verify user!"
        db.addReview(reviewObj, conn)
        conn.commit()
        return "Success"
    else:
        return "Problem handling review! Recieved"

@app.route('/deleteReview', methods=['POST'])
def deleteReview():
    """
    Recieves JSON review object from javascript as ajax request.
    """
    conn = get_db()
    print("delete review called. Raw data:")
    print(request.data)
    reviewObj = request.get_json()

    if reviewObj:
        if (not reviewObj.get("time")) or (not reviewObj.get("user")):
            return "Failure: Time or user or both not provided!!"
        return db.deleteReview(reviewObj, conn)
    else:
        return "reviewObj = None (or reviewObj = []). type = {}".format(type(reviewObj))


@app.route('/getReviews-<rID>')
def getReviews(rID):
    if db.getReviews(rID, get_db()) == None:
        return "[]"
    else:
        return db.getReviews(rID, get_db())

@app.route('/restaurants/?ID=<restaurantID>', methods=['GET', 'POST'])
def restaurantDetails(restaurantID):
    conn = get_db()
    albums = db.getAlbumsFromRestaurant(conn, restaurantID)
    if albums:
        for album in albums:
            album["images"] = json.loads(album["imagesJSON"])

    restaurant = db.getRestaurant(conn, restaurantID)
    pprint.pprint(restaurant["address"])
    restaurant["address"] = restaurant["address"].strip()
    print(albums)
    return render_template('restaurant.html', restaurant=restaurant, albums=albums, showAlb=False)

@app.route('/restaurants/?ID=<restaurantID>?showMenu=<albumID>', methods=['GET', 'POST'])
def showRestaurantMenu(restaurantID, albumID):
    conn = get_db()
    print("Fetching album to display")
    album = db.getAlbum(conn, albumID)
    album["images"] = json.loads(album["imagesJSON"])
    restaurant = db.getRestaurant(conn, restaurantID)
    restaurant["address"] = restaurant["address"].strip()
    return render_template('restaurant.html', restaurant=restaurant, album=album, showAlb=True)

@app.route('/add-food-photo', methods=['POST'])
def addFoodPhoto():
    print("add food photo requested. request object:")
    pprint.pprint(request.files)
    pprint.pprint(request.files.get("foodPhoto"))

    conn = get_db()

    albumID = request.values.get("albumID")
    username = request.values.get("username")
    fromURL = request.values.get("cameFrom")
    image = request.files.get("foodPhoto")

    # If any required params post data missing
    if None in [albumID, fromURL, username, image]:
        print("Something = None in:")
        pprint.pprint({"albumID": albumID, "fromURL": fromURL, "username": username, "image": image})
        return redirect("/desktop/")

    if image.filename != '' and '.' in image.filename and \
        image.filename.rsplit('.',1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS:
            uploadedFilePath = db.addUploadedImage(image)

    # Update the imagesJSON with the new image object.
    conn.execute("UPDATE album SET imagesJSON = ? WHERE id = ?",
        (json.dumps((json.loads((conn.execute("SELECT imagesJSON FROM album WHERE id = ?", (albumID,))).fetchone()[0])) + [{"imageURL" : uploadedFilePath, "username" : username, "timestamp" : int(time.time())}]),
        albumID))
        # sorry lol

    conn.commit()

    # Back to original URL
    return redirect(fromURL)

@app.route('/nearbyFood/')
def nearbyPage():
    return render_template('foodsNearby.html')


@app.route('/nearby/', methods=['GET', 'POST'])
def nearby():
    # Try get X and Y coordinates incase they were sent with the request
    x = request.values.get('X')
    y = request.values.get('Y')
    if not x and not y:
        # Get x and y using ip:
        # When server running on your own computer this will just be 127.0.0.1.
        # suggest making some hardcoded tests for external IP's e.g. 129.94.8.93 = UNSW
        userIP = request.remote_addr
        print("userIP = {}".format(userIP))
        # Use some geo ip library or something to approximate loc.
        reader = geoip2.database.Reader('GeoLite2-City.mmdb');
        try:
            response = reader.city(userIP);
            x = response.location.latitude;
            y = response.location.longitude;
        except AddressNotFoundError:
            #return an empty list
            return list();
        reader.close();

    x = float(x)
    y = float(y)

    unsortedListOfFoods = db.getAllAlbums(get_db())
    # For e.g. contains:

    # [{'categories': 'Asian',
    #  'coverImage': None,
    #  'id': 1,
    #  'name': 'Dimsum',
    #  'restaurant': '9'},
    # {'categories': 'Asian',
    #  'coverImage': None,
    #  'id': 2,
    #  'name': 'Korean Chicken',
    #  'restaurant': '4'},.......

    restaurants = db.restaurantsToListOfDicts(get_db())

    for r in restaurants:
        r['dist'] = ((x-r['coordsX'])**2+(y-r['coordsY'])**2)**(1/2)

    # Bubble sort list of restaurants by distance
    for i in range(0,len(restaurants)):
        for j in range(i,len(restaurants)):
            if restaurants[j]['dist'] < restaurants[i]['dist']:
                restaurants[i], restaurants[j] = restaurants[j], restaurants[i]

    sortedListOfFoods = []
    for r in restaurants:
        for j in unsortedListOfFoods:
            print("Comparing restaurant {} with food {}".format(r, j))
            if int(j['restaurant']) == r['ID']:
                sortedListOfFoods += [j]
                sortedListOfFoods[-1]['dist from user'] = r['dist']

    # e.g. restaurants[0]["ID"] or restaurants[0]["coordsX"]
    # Example:

    # [{'ID': 1,
    #  'address': '10 Dixon Street, Chinatown, Sydney',
    #  'categories': 'Asian',
    #  'coordsX': -33.8767535,
    #  'coordsY': 151.2018453,
    #  'imageURL': '/static/images/restaurants/oldtown.jpg',
    #  'name': 'Old Town ',
    #  'phone': '(02) 9264 3888',
    #  'views': 1},
    # {'ID': 2,
    #  'address': '100 John St, Cabramatta NSW 2166',
    #  'categories': 'Asian',
    #  'coordsX': -33.8950346,
    #  'coordsY': 150.9319742,
    #  'imageURL': '/static/images/restaurants/tanviet.jpg',
    #  'name': 'Tan Viet Noodle House',
    #  'phone': '(02) 9727 6853',
    #  'views': 2},......

    # Now return sorted list of foods using their restaurants locations

    return jsonify(["{} foods from {} restaurants sorted by distance from S {}, E {}".format(len(sortedListOfFoods), len(restaurants), x, y), sortedListOfFoods])


if __name__ == '__main__':

    app.config['SECRET_KEY']='82A71D784E477214F3772435473A1'
    app.config['SESSION_COOKIE_NAME']='flasksession'

    # pprint.pprint(app.config)

    # Using 0.0.0.0 will make sure the app is externally visible
    # i.e. can be accessed over LAN (or WAN if the port is forwarded)
    # The server should be accessible at http://127.0.0.1:5000/ once run
    if len(argv) > 1:
        # if running in production
        if portNum == 443:
            app.run(debug=False, host='0.0.0.0', port=portNum, ssl_context=('munchr.pem','munchr.key'))
        else:
            app.run(debug=True, host='0.0.0.0', port=portNum)
    else:
        print("Usage: app.py <port>", file = stderr)

    # NB The server will restart whenever there is a change to any of
    # the .py files. (html/css/js you will have to do a hard page
    # refresh from in browser or turn off caching and refresh normally)
