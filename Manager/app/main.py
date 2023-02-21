
from flask import render_template, url_for, request
from app import manager
from flask import json


@manager.route('/')
def main():
    return render_template("main.html")

