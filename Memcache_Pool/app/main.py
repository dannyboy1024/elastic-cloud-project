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
        response = memcachePool.response_class(
            response=json.dumps("Not in cache"),
            status=400,
            mimetype='memcachePool/json'
        )
    else:
        print('cache success')
        value = res.content
        response = memcachePool.response_class(
            response=json.dumps(value),
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
    key = request.args.get('key')
    value = request.args.get('value')
    requestJson = {
        'key': key,
        'value': value
    }
    cache_partition = check_partition(key)
    node_num = cache_partition % memcache_pool_tracker.num_active_instances
    node_instance = memcache_pool_tracker.available_instances[node_num]
    node_ip = memcache_pool_tracker.instances_ip[node_instance]
    url = 'http://'+str(node_ip)+':5000'
    res = requests.post(url + '/put', params=requestJson)
    if res.status_code == 200:
        if key not in memcache_pool_tracker.all_keys_with_node:
            memcache_pool_tracker.all_keys_with_node[key] = node_num
            memcache_pool_tracker.num_items += 1
        response = memcachePool.response_class(
            response=json.dumps("OK"),
            status=200,
            mimetype='application/json'
        )
    else:
        response = memcachePool.response_class(
            response=json.dumps("Size too big"),
            status=400,
            mimetype='application/json'
        )
    return response

@memcachePool.route('/manual_change', methods=['POST'])
def manual_change():
    change = request.args.get('change')
    memcache_pool_tracker.manual_change(change)
    response = memcachePool.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )
    return response

@memcachePool.route('/auto_change', methods=['POST'])
def auto_change():
    change = request.args.get('change')
    memcache_pool_tracker.auto_change(change)
    response = memcachePool.response_class(
        response=json.dumps("OK"),
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

@memcachePool.route('/getNumNodes', methods=['POST'])
def getNumNodes():
    numNodes = memcache_pool_tracker.num_active_instances
    response = memcachePool.response_class(
        response=json.dumps(numNodes),
        status=200,
        mimetype='memcachePool/json'
    )
    return response

@memcachePool.route('/all_keys', methods=['POST'])
def list_all_keys():
    all_keys = memcache_pool_tracker.all_keys_with_node.keys()
    all_keys_response = list(all_keys)
    resp = {
        "success" : "true", 
        "all_keys": all_keys_response
    }
    response = memcachePool.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='memcachePool/json'
    )
    return response

@memcachePool.route('/configure', methods=['POST'])
def configure():
    pass