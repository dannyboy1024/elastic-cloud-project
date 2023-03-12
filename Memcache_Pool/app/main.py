from flask import render_template, url_for, request
from app import memcachePool, memcache_pool_tracker, memcache_pool_tracking, provision_ec2, check_partition
from flask import json
from collections import OrderedDict
import base64
import logging
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
import os
import time
import atexit
import requests
import boto3
from datetime import datetime

provision_ec2()

def updCacheStatsToCloudWatch():

    #get stats
    print("Uploading stats ...")
    numActiveNodes = memcache_pool_tracker.num_active_instances
    numHitReqs     = memcache_pool_tracker.num_hit_request
    numMissReqs    = memcache_pool_tracker.num_miss_request 
    numTotalReqs   = numHitReqs + numMissReqs
    numItems       = memcache_pool_tracker.num_items
    totalSize      = memcache_pool_tracker.total_size


    #upload stats to cloudwatch
    cloudwatch = boto3.client(
        'cloudwatch',
        region_name='us-east-1',
        aws_access_key_id = 'AKIAVW4WDBYWC5TM7LHC',
        aws_secret_access_key = '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'
    )
    response = cloudwatch.put_metric_data (
        Namespace = 'Cache Stats',
        MetricData = [
            {
                'MetricName': 'numActiveNodes',
                'Timestamp': datetime.utcnow(),
                'Unit': 'None',
                'Value': numActiveNodes
            },
            {
                'MetricName': 'numTotalRequests',
                'Timestamp': datetime.utcnow(),
                'Unit': 'None',
                'Value': numTotalReqs
            },
            {
                'MetricName': 'numMissRequests',
                'Timestamp': datetime.utcnow(),
                'Unit': 'None',
                'Value': numMissReqs
            },
            {
                'MetricName': 'numItems',
                'Timestamp': datetime.utcnow(),
                'Unit': 'None',
                'Value': numItems
            },
            {
                'MetricName': 'totalSize',
                'Timestamp': datetime.utcnow(),
                'Unit': 'None',
                'Value': totalSize                
            }
        ]
    )

    #reset number of hit/miss requests
    memcache_pool_tracker.num_hit_request  = 0
    memcache_pool_tracker.num_miss_request = 0


scheduler = BackgroundScheduler()
scheduler.add_job(func=updCacheStatsToCloudWatch, trigger="interval", seconds=5)
scheduler.start()
atexit.register(lambda: scheduler.shutdown()) # Shut down the scheduler when exiting the app


@memcachePool.route('/')
def main():
    return render_template("main.html")

@memcachePool.route('/getImage', methods=['POST'])
def getImage():
    """
    Fetch the value from the memcache given a key
    key: string
    """
    key = request.args.get('key')
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
        memcache_pool_tracker.num_miss_request += 1
        response = memcachePool.response_class(
            response=json.dumps("Not in cache"),
            status=400,
            mimetype='application/json'
        )
    else:
        #print('cache success')
        memcache_pool_tracker.num_hit_request += 1
        json_response = res.json()
        value = json_response["value"]
        resp = {
            "success" : "true", 
            "value": value
        }
        response = memcachePool.response_class(
            response=json.dumps(resp),
            status=200,
            mimetype='application/json'
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
    imageSize = request.args.get('size')
    requestJson = {
        'key': key,
        'value': value, 
        'size': imageSize
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
        resp = {
            "success" : "true"
        }
        response = memcachePool.response_class(
            response=json.dumps(resp),
            status=200,
            mimetype='application/json'
        )
    else:
        resp = {
            "success" : "false"
        }
        response = memcachePool.response_class(
            response=json.dumps(resp),
            status=400,
            mimetype='application/json'
        )
    return response

@memcachePool.route('/manual_change', methods=['POST'])
def manual_change():
    change = request.args.get('change')
    memcache_pool_tracker.manual_change(change)
    resp = {
        "success" : "true"
    }
    response = memcachePool.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response

@memcachePool.route('/auto_change', methods=['POST'])
def auto_change():
    change = request.args.get('change')
    memcache_pool_tracker.auto_change(change)
    resp = {
        "success" : "true"
    }
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
    memcache_pool_tracker.all_keys_with_node = {}
    memcache_pool_tracker.total_size = 0
    memcache_pool_tracker.num_items = 0
    resp = {
        "success" : "true"
    }
    response = memcachePool.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
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
        mimetype='application/json'
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
        mimetype='application/json'
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
        arg_ratio = request.args.get('expRatio')
        if arg_ratio != "": 
            expRatio = float(arg_ratio)
            memcache_pool_tracker.expand_ratio_change(expRatio)
    if 'shrinkRatio' in request.args: 
        arg_ratio = request.args.get('shrinkRatio')
        if arg_ratio != "": 
            shrinkRatio = float(arg_ratio)
            memcache_pool_tracker.shrink_ratio_change(shrinkRatio)
    if single_cache_configure != {}:
        memcache_pool_tracker.configureNodes(single_cache_configure)
    resp = {
        "success" : "true"
    }
    response = memcachePool.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response