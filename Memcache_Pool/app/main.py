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

@memcachePool.route('/getImage', methods=['POST'])
def getImage():
    """
    Fetch the value from the memcache given a key
    key: string
    """
    key = request.form.get('key')
    requestJson = {
        'key': key
    }
    cache_partition = check_partition(key)
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
        memcache_pool_tracker.update_key_tracking()
        memcache_pool_tracker.update_total_size()
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
    resp = {
        "numNodes": numNodes
    }
    response = memcachePool.response_class(
        response=json.dumps(resp),
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
    single_cache_configure = {}
    if 'mode' in request.args: 
        mode = request.args.get('mode')
        memcache_pool_tracker.mode_change(mode)
    if 'numNodes' in request.args: 
        numNodes = int(request.args.get('numNodes'))
        memcache_pool_tracker.numNode_change(numNodes)
    if 'cacheSize' in request.args: 
        single_cache_configure["size"] = int(request.args.get('cacheSize'))
    if 'policy' in request.args: 
        single_cache_configure["mode"] = request.args.get('policy')
    if 'expRatio' in request.args: 
        expRatio = float(request.args.get('expRatio'))
        memcache_pool_tracker.expand_ratio_change(expRatio)
    if 'shrinkRatio' in request.args: 
        shrinkRatio = float(request.args.get('shrinkRatio'))
        memcache_pool_tracker.shrink_ratio_change(shrinkRatio)
    if single_cache_configure != {}:
        memcache_pool_tracker.configureNodes(single_cache_configure)

    response = memcachePool.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='memcachePool/json'
    )
    return response