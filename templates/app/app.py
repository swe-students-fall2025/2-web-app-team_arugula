import os
import json
import datetime
import logging
import gridfs
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
photos_collection.create_index([('location', '2dsphere')])
fs = gridfs.GridFS(db)

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
    user_data = users_collection.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

def load_username(username):
    user_data = users_collection.find_one({"username": username})
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
    return render_template('login.html', register=True)

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
    return render_template('login.html', register=False)

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

# profile page lets you change your username, password, email, privacy settings, click save button to finalize changes
@app.route("/profile")
@login_required
def profile():
    if request.method == "POST":
        new_username = request['username']
        new_email = request['email']
        new_password = request['password']
        update = {}
        if new_username:
            update["username"] = new_username
        if new_email:
            update["email"] = new_email
        if new_password:
            update["password_hash"] = generate_password_hash(new_password)
        if update:
            users_collection.update_one({"_id": ObjectId(current_user.id)}, {"$set": update})
            flash("Profile updated!")
    user_data = users_collection.find_one({"_id": ObjectId(current_user.id)})
    return render_template("your_profile.html", user=user_data)

# let a client add data to database like photos, then return them to the home page
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files["image"]
        species = request.form["species"]
        latitude = request.form["latitude"]
        longitude = request.form["longitude"]
        if not file or not species or not latitude or not longitude:
            flash("Oopsie poopsie! Missing image")
            return redirect(url_for("upload"))
        data = file.read()
        if len(data) > UPLOAD_MAX_BYTES:
            flash("Oopsie poopsie! :( File too big!")
            return redirect(url_for("upload"))
        if not allowed_image(data):
            flash("Oopsie poopsie! :( We don't allow that type of images!")
            return redirect(url_for("upload"))
        filename = secure_filename(file.filename)
        file_id = fs.put(data, filename=filename, contentType=file.mimetype, uploaded_by=ObjectId(current_user.id))
        image_data = {
            "uploader_id": ObjectId(current_user.id),
            "uploader_username": current_user.username,
            "species": species,
            "image_fs_id": file_id,
            "created_at": datetime.datetime.utcnow(),
            "location": {
                "type": "Point",
                "coordinates": [float(latitude), float(longitude)]
            }
        }
        photos_collection.insert_one(image_data)
        flash("Yipee-ai-oh-kay-ay! :D Successfully uploaded another photo! Gotta catch 'em all!")
        return redirect(url_for("your_observations"))
    return render_template("upload.html")

# get images
@app.route("/image/<img_id>")
def get_image(img_id):
    try:
        grid_out = fs.get(ObjectId(img_id))
    except Exception:
        return "Not found", 404
    return send_file(BytesIO(grid_out.read()), mimetype=grid_out.content_type, download_name=grid_out.filename)
    
# gallery page
@app.route("/my_observations")
@login_required
def your_observations():
    obs = list(db.observations.find({"uploader_id": ObjectId(current_user.id)}).sort("created_at", -1))
    return render_template("your_observations.html", observations=obs)

# your feed page lets you search someone's username, or a plant/animal name, and it returns relevant photos from that username or of that species
# feed page shows a map of where a species' photo was taken
@app.route("/feed")
@login_required
def feed():
    return render_template("feed.html")

# get coordinates of observations, plus species and username of uploader
@app.route("/api/observations")
def api_observations():
    species = request.args.get("species")
    username = request.args.get("username")
    q = {}
    if species:
        q["species"] = {"$regex": species, "$options": "i"}
    if username:
        q["uploader_username"] = {"$regex": username, "$options": "i"}
    docs = photos_collection.find(q)
    features = []
    for d in docs:
        features.append({
            "type": "Feature",
            "properties": {
                "id": str(d["_id"]),
                "species": d.get("species"),
                "uploader": d.get("uploader_username"),
                "image_url": url_for("get_image", img_id=str(d["image_fs_id"]))
            },
            "geometry": d.get("location")
        })
    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })

# search for user or images of species
@app.route("/search", methods=["GET"])
@login_required
def search():
    q = request.args.get("q", "")
    results = []
    if q:
        results = list(photos_collection.find({
            "$or": [
                {"species": {"$regex": q, "$options": "i"}},
                {"uploader_username": {"$regex": q, "$options": "i"}}
            ]
        }))
    return render_template("search_others_observations.html", observations=results, q=q)
    
# encyclopedia page lists all the species you've taken photos of, and each of their biological information 
# encyclopedia will quote Wikipedia or Encyclopedia Britannica
@app.route("/encyclopedia/<species>")
def encyclopedia(species):
    encyclopedia_collection = db['encyclopedia']
    species_data = encyclopedia_collection.find_one({"species": species})
    if not species_data or (datetime.datetime.utcnow() - doc["cached_at"]).days > 30:
        summary = get_wikipedia(species)
        if not summary:
            return render_template("encyclopedia.html", species=species, summary="Sorry! No info found.")
        species_data = {
            "species": species,
            "summary": summary,
            "cached_at": datetime.datetime.utcnow()
        }
        encyclopedia_collection.update_one({"species": species}, {"$set": doc}, upsert=True)
    return render_template("encyclopedia.html", species=species, summary=doc["summary"])

def get_wikipedia(species):
    try:
        res = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{species}",
            timeout=5
        )
        if res.status_code == 200:
            data = res.json()
            return data.get("extract")  # plain text summary
    except Exception as e:
        print("Oopsie poopsie! :( Here's your error:", e)
    return None 

# home page contains only a few pictures, click on gallery link to view more pictures and all that you've taken
@app.route("/")
@login_required
def home():
    # show profile summary + gallery preview
    recent = list(db.observations.find({"uploader_id": ObjectId(current_user.id)}).sort("created_at", -1).limit(8))
    return render_template("home.html", recent=recent)


if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    FLASK_ENV = os.getenv("FLASK_ENV")
    print(f"FLASK_ENV: {FLASK_ENV}, FLASK_PORT: {FLASK_PORT}")
    app.run(debug=True, port=FLASK_PORT)

    # if client cannot connects to MongoDB, then take them to error page 
    @app.errorhandler(Exception)
    def handle_error(e):
        return render_template("error.html", error=e)









