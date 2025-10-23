from flask_pymongo import PyMongo
from flask import Flask
from flask_login import UserMixin, LoginManager
from dotenv import load_dotenv
import os
import logging


# load the environment variables
load_dotenv() 

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["temp2"] = "temp3"  # Replace with your MongoDB URI
mongo = PyMongo(app)

client = MongoClient("mongodb://localhost:27017/")
db = client["user_db"]
users = db["users"]

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    user_data = users.find_one({"_id": ObjectId(user_id)})
    if user_data:
      return User(user_data)
    return None

class User(UserMixin):
  def __init__(self, user_data):
    self.user_data = user_data
    self.id = str(user_data['_id']) 

# Implement required methods/properties from UserMixin

