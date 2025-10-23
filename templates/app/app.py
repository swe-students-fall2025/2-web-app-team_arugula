import os
import json
import datetime
import logging
from flask_pymongo import PyMongo
from pymongo import MongoClient
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, dotenv_values



# load the environment variables 
load_dotenv() 

# set up the app
# get the HTML webpages and CSS styles
app = Flask(__name__, template_folder="templates", static_folder="static")
    
# get the env variables
config = dotenv_values()
app.config.from_mapping(config)

# get the client, and the database
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
users_collection = db["users"]
photos_collection = db["photos"]

# client logs in 
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        
@login_manager.user_loader
def load_user(user_id):
    user_data = users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

def load_username(username):
    user_data = users.find_one({"username": username})
    if user_data:
        return User(user_data)
    return None

# get the home page
@app.route("/")
def home():
    docs = db.messages.find({}).sort("created_at", -1)
    return render_template("home.html", docs=docs)

# get the username and password from login.html
# check if it's the right combination in the MongoDB database
# if yes, then login is successful, take user to home.html
# if not (either username or password is incorrect), user stays on login.html, tell user to try again

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        
        user_data = users_collection.find_one({'username': username})
        if user_data:
            flash("Oopsie poopsie! :( That username's taken!")
            return redirect(url_for('register'))
        record = users_collection.insert_one({
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.datetime.utcnow()
        })
        user = User(record.inserted_id)
        login_user(user)
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_data = users_collection.find_one({'username': username})
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash("Oopsie poopsie! :( Incorrect username or password (or both!)")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# get the database of usernames, passwords, images, encyclopedia articles, etc. 

# after you log in, go to home page 
# your home page has your "Welcome [username]!", profile picture, and a gallery of pictures of plants/animals you took
# Write python code to get photos you have posted, and for your feed page, get photos that your friends have posted
# Get images from MongoDB, display them with HTML and CSS
@app.route("/profile", methods=['GET', 'POST])
@login_required
def profile():
                                
# let a client add data to database like photos, then return them to the home page
@app.route("/create", methods=["POST"])
def create_post():
    name = request.form["fname"]
    message = request.form["fmessage"]
        
    doc = {
        "name": name,
        "message": message,
        "created_at": datetime.datetime.utcnow(),
    }
    db.messages.insert_one(doc)
    return redirect(url_for("home"))

    # let a client edit existing data, like on the profile or gallery pages
    @app.route("/edit/<post_id>")
    def edit(post_id):
        doc = db.messages.find_one({"_id": ObjectId(post_id)})
        return render_template("edit.html", doc=doc)
        
    @app.route("/edit/<post_id>", methods=["POST"])
    def edit_post(post_id):
        name = request.form["fname"]
        message = request.form["fmessage"]
        doc = {
            "name": name,
            "message": message,
            "created_at": datetime.datetime.utcnow(),
        }
        db.messages.update_one({"_id": ObjectId(post_id)}, {"$set": doc})
        return redirect(url_for("home"))

    # let a client delete a record
    @app.route("/delete/<post_id>")
    def delete(post_id):
        db.messages.delete_one({"_id": ObjectId(post_id)})
        return redirect(url_for("home"))

    # let a client delete a record according to author and contents of post
    @app.route("/delete-by-content/<post_name>/<post_message>", methods=["POST"])
    def delete_by_content(post_name, post_message):
        db.messages.delete_many({"name": post_name, "message": post_message})
        return redirect(url_for("home"))

    # if client cannot connects to MongoDB, then take them to error page 
    @app.errorhandler(Exception)
    def handle_error(e):
        return render_template("error.html", error=e)


# set the env variables
if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    FLASK_ENV = os.getenv("FLASK_ENV")
    print(f"FLASK_ENV: {FLASK_ENV}, FLASK_PORT: {FLASK_PORT}")

    app.run(port=FLASK_PORT)


# profile page lets you change your username, password, email, privacy settings, click save button to finalize changes

# home page contains only a few pictures, click on gallery link to view more pictures and all that you've taken
# gallery page

# your feed page lets you search someone's username, or a plant/animal name, and it returns relevant photos from that username or of that species
# feed page shows a map of where a species' photo was taken

# encyclopedia page lists all the species you've taken photos of, and each of their biological information 
# encyclopedia will quote Wikipedia or Encyclopedia Britannica








# Implement required methods/properties from UserMixin

