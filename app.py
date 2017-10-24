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
#import db

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

    return render_template('home.html')


@app.route('/')
def rootRedirect():
    return redirect('/desktop/')


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
