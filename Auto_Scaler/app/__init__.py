from flask import Flask
from flask_cors import CORS

autoScaler = Flask(__name__)
autoScaler.config.from_object(__name__)

CORS(autoScaler, resources={r"/*":{'origins':'*'}})

