from flask import render_template, url_for, request
from app import memcachePool, memcache_pool_tracker, memcache_pool_tracking, provision_ec2, check_partition
from flask import json
from collections import OrderedDict
import base64
import logging
from pathlib import Path
#from apscheduler.schedulers.background import BackgroundScheduler
import os
import time
import atexit
import requests
import boto3

provision_ec2()

@memcachePool.route('/')
def main():
    return render_template("main.html")

@memcachePool.route('/key/<key_value>', methods=['POST'])
def getImage(key_value):
    """
    Fetch the value from the memcache given a key
    key: string
    """
    requestJson = {
        'key': key_value
    }
    cache_partition = check_partition(key_value)
    node_num = cache_partition % memcache_pool_tracker.num_active_instances
    node_instance = memcache_pool_tracker.available_instances[node_num]
    node_ip = memcache_pool_tracker.instances_ip[node_instance]
    url = 'http://'+str(node_ip)+':5000'
    res = requests.post(url + '/get', params=requestJson)

    if res.status_code == 400:
        content = res.json()
        response = memcachePool.response_class(
            response=json.dumps({
                "success": "false",
                "error": {
                    "code": 400,
                    "message": content
                    }
            }),
            status=200,
            mimetype='memcachePool/json'
        )
        return response
    else:
        print('cache success')
        content = base64.b64decode(res.content)
        response = memcachePool.response_class(
            response=json.dumps(json.dumps({
                    "success": "true",
                    "key": key_value,
                    "content": bytes.decode(content)
                }),),
            status=200,
            mimetype='memcachePool/json'
        )
        return response


@memcachePool.route('/put', methods=['POST'])
def put():
    """
    Upload the key/value pair to the memcache
    key: string
    value: string (For images, base64 encoded string)
    """
    key = request.form.get('key')
    image = request.files.get('file')
    imageBytes = image.read()
    encodedImage = base64.b64encode(str(imageBytes).encode())
    requestJson = {
        'key': key,
        'value': encodedImage
    }
    cache_partition = check_partition(key)
    node_num = cache_partition % memcache_pool_tracker.num_active_instances
    node_instance = memcache_pool_tracker.available_instances[node_num]
    node_ip = memcache_pool_tracker.instances_ip[node_instance]
    url = 'http://'+str(node_ip)+':5000'
    res = requests.post(url + '/put', params=requestJson)

    resp = OrderedDict([("success", "true"), ("key", [key])])
    response = memcachePool.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response



@memcachePool.route('/clear', methods=['POST'])
def clear():
    """
    Remove all contents in the memcache
    No inputs required
    """
    for id in memcache_pool_tracker.active_instances:
        node_ip = memcache_pool_tracker.active_instances[id]
        url = 'http://'+str(node_ip)+':5000'
        requests.post(url + '/clear')
    memcache_pool_tracker.total_size = 0
    memcache_pool_tracker.num_items = 0
    response = memcachePool.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='memcachePool/json'
    )
    return response

