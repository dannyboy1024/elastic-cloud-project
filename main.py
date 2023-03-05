from flask import Flask, jsonify
from flask_cors import  CORS

webapp = Flask(__name__)
# webapp.config.from_object(__name__)
# CORS(webapp,resources={r"/*":{'origins': "*"}})
# CORS(webapp,resources={r"/*":{'origins': "http://localhost:8080","allow_headers": "Access-Control-Allow-Origin"}})



@webapp.route('/', methods = ['GET'])
def hello():
    return jsonify({"hi":"wkx"})


if __name__ == "__main__":
    webapp.run(debug=True)