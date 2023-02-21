
from flask import render_template, url_for, request
from app import memcachePool
from flask import json


@memcachePool.route('/')
def main():
    return render_template("main.html")

