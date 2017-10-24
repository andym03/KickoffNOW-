#!/usr/bin/python3

import sqlite3, pprint, json, time
from os import listdir

def searchRestaurant(cur, query):
    cur.execute("SELECT * FROM restaurants WHERE name LIKE ('%' || ? || '%') ORDER BY ratings DESC",(query,))
    return cur.fetchall()

def getAllAlbums(conn):
    rows = [dict(row) for row in conn.execute("SELECT * FROM album")]
    # This function doesn't care about leaving the connection open...
    return rows

def getAlbum(conn, albumID):
    cur = conn.execute("SELECT * FROM album WHERE id = (?)", (albumID, ))
    return dict(cur.fetchone())

def searchAlbum(cur, query):
    return [dict(row) for row in cur.execute("SELECT * FROM album WHERE categories LIKE ('%' || ? || '%')",(query,))]

def searchAlbumName(cur, query):
    return [dict(row) for row in cur.execute("SELECT * FROM album WHERE name LIKE ('%' || ? || '%')",(query,))]

def searchAlbumAll(cur, query):
    return [dict(row) for row in cur.execute("SELECT * FROM album WHERE categories LIKE ('%' || ? || '%') OR name LIKE ('%' || ? || '%')",(query, query, ))]

def restaurantNameFromID(ID, conn):
    # First row
    cursor = conn.execute("SELECT name FROM restaurants WHERE ID = ?", (ID,))
    restaurantRow = dict(cursor.fetchone())
    return restaurantRow.get("name")

def getAlbumsFromRestaurant(conn, restaurant_id):
    return [dict(row) for row in conn.execute("SELECT * FROM album WHERE restaurant = (?)", (restaurant_id, ))]

def getPopularRestaurants(conn):
    cur = conn.execute("SELECT * FROM restaurants ORDER BY views DESC LIMIT 12")
    return cur.fetchall()

def getRestaurant(conn, ID):
    conn.execute("UPDATE restaurants SET views = views + 1 WHERE ID = (?)", (ID, ))
    cur = conn.execute("SELECT * FROM restaurants WHERE ID = (?)", (ID, ))
    return dict(cur.fetchone())

def categoriesToList(conn):
    categories = list({row[0] for row in conn.execute("SELECT categories FROM album")})
    return categories

def restaurantNamesToList(conn):

    curs = conn.execute("SELECT name FROM restaurants")

    names = list({name[0] for name in curs.fetchall()})

    return names

def restaurantsToListOfDicts(conn):

    rows = [dict(row) for row in conn.execute("SELECT * from restaurants")]

    return rows

def getRestaurantID(name, conn):
    # First row
    cursor = conn.execute("SELECT ID FROM restaurants WHERE name = ?", (name,))
    restaurantRow = cursor.fetchone()
    return restaurantRow['ID']

def addAlbum(foodObj, username, conn):

    print("Add to album:")
    print(foodObj)
    # Add entry into food table in db
    conn.execute("INSERT INTO album (name, categories, imagesJSON, restaurant, addedUsername) values (?,?,?,?,?)",
            (foodObj['name'],
            foodObj['categories'],
            json.dumps([{"imageURL" : foodObj['imageURL'], "username" : username, "timestamp" : int(time.time())}]),
            foodObj['restaurant'],
            username)
            )

    conn.commit()

    ID = conn.execute("SELECT id FROM album WHERE name = ?", (foodObj["name"],)).fetchone()[0]
    return ID

def addRestaurantEntry(restaurantObj, username, conn):
    #adds entry into restaurant table in db
    conn.execute("INSERT INTO restaurants (name, categories, imageURL, phone, address, coordsX, coordsY, views, addedUsername, ratings) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ( restaurantObj['name'],
            restaurantObj['categories'],
            restaurantObj['imageURL'],
            restaurantObj['phone'],
            restaurantObj['address'],
            restaurantObj['coordsX'],
            restaurantObj['coordsY'],
            0,
            username,
            3)
            )
    conn.commit()

    ID = conn.execute("SELECT ID FROM restaurants WHERE name = ?", (restaurantObj["name"],)).fetchone()[0]

    return ID


def addReview(reviewObj, conn):
    cursor = conn.execute("SELECT reviewsJSON FROM restaurants WHERE ID = ?", (reviewObj["restaurantID"],))

    prevJSON = dict(cursor.fetchone()).get("reviewsJSON")

    # First make our new list element for this review
    review = {
        "text" : reviewObj["reviewText"],
        "rating" : reviewObj["reviewRating"],
        "user" : reviewObj["username"],
        "userID" : reviewObj["userID"],
        "time" : str(int(time.time()))  # Seconds since epoch
        }

    newReviewsObj =  json.loads(prevJSON) + [review] if prevJSON else [review]
    conn.execute("UPDATE restaurants SET reviewsJSON = ? WHERE ID = ?", (json.dumps(newReviewsObj), reviewObj["restaurantID"]))

def deleteReview(reviewObj, conn):

    # ERL = Existing Review list
    # ERJ = Existing Review JSON

    cursor = conn.execute("SELECT reviewsJSON FROM restaurants WHERE ID = ?", (reviewObj["restaurantID"],))
    ERJ = dict(cursor.fetchone()).get("reviewsJSON")

    print("This is what was in the database:")
    pprint.pprint(ERJ)

    if ERJ:
        try:
            ERL = json.loads(ERJ)
            for i in range(len(ERL)):
                print("testing against {}".format(ERL[i]))
                if [ERL[i]["time"], ERL[i]["user"]] == [reviewObj["time"], reviewObj["user"]]:
                    print("FOUND IT")
                    ERL = ERL[:i] + ERL[i+1:]  # Existing list without this element
                    conn.execute("UPDATE restaurants SET reviewsJSON = ? WHERE ID = ?", (json.dumps(ERL), reviewObj["restaurantID"]))
                    conn.commit()
                    return "Success"
        except Exception as e:
            return "Failure: {}.".format(e)

        return "Failure: Couldnt find the review post in existing JSON."
    else:
        return "Failure: couldnt get JSON for existing reviews object."

#TODO: Maybe make thread safe, it currently REALLY isn't
#      Should be okay for the demo, though
def addUploadedImage(image):
    #adds the image to the site, returns the path to the image
    extension = image.filename.rsplit('.',1)[1].lower()
    existingFiles = listdir("static/user-uploads")
    i = 0
    while (str(i) + "." + extension) in existingFiles:
        i += 1
    pathToSaveAs = "static/user-uploads/" + str(i) + "." + extension
    image.save(pathToSaveAs)
    return "/" + pathToSaveAs

def getReviews(restaurantID, conn):
    try:
        return conn.execute("SELECT reviewsJSON FROM restaurants WHERE ID = ?", (restaurantID,)).fetchone()[0]
    except Exception as e:
        return str(e)


# Testing individual functions without running whole website
if __name__ == '__main__':
    conn = sqlite3.connect("database.db")
    print(restaurantNamesToList(conn))
    print(categoriesToList(conn))
    conn.commit()
    conn.close()

    conn2 = sqlite3.connect("database.db")
    conn2.row_factory = sqlite3.Row
    print(getAllAlbums(conn2))

    pprint.pprint(restaurantsToListOfDicts(conn2))

    for rest in restaurantNamesToList():
        print(getRestaurantID(rest))
    conn2.close()
