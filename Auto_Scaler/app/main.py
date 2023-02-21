
from flask import render_template, url_for, request
from app import autoScaler
from flask import json


@autoScaler.route('/')
def main():
    return render_template("main.html")

