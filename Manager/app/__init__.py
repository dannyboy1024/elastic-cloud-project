from flask import Flask
from flask_cors import CORS
import boto3

class FILEINFO:
    def __init__(self, key, location):
        self.key = key
        self.location = location

class AWS_boto_services:
    def __init__(self) -> None:
        self.ec2 = boto3.client("ec2")
        self.s3 = boto3.client("s3")
        self.rds = boto3.client("rds")


manager = Flask(__name__)
CORS(manager)
from app import main




