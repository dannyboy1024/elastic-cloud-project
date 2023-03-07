from flask import Flask
from flask_cors import CORS
import boto3

class FILEINFO:
    def __init__(self, key, location):
        self.key = key
        self.location = location

manager = Flask(__name__)
CORS(manager)
from app import main




