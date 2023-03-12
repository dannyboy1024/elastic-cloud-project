
from flask import render_template, url_for, request, session
from app import manager, db, FILEINFO

from flask import json
from collections import OrderedDict
import boto3
from pathlib import Path
import os
import hashlib
import base64
import requests
import plotly.graph_objs as go
import pytz
from datetime import datetime, timedelta

os_file_path = os.getcwd()
bucket_name = 'ece1779-winter23-a2-bucket'
manager_url = 'http://127.0.0.1:5000'
memcache_pool_url = 'http://127.0.0.1:5002'
autoscaler_url = 'http://127.0.0.1:5003'

def provision_aws():
    global s3client
    global rds_client
    s3client = boto3.client('s3', region_name='us-east-1')
    rds_client = boto3.client('rds', region_name='us-east-1')
    print("Provision done")

#@mock_s3
def test_bucket():
    s3client = boto3.client('s3', region_name='us-east-1')
    
    #response = s3client.create_bucket(Bucket=bucket_name)
    #print(response)
    with open("test.txt", "w") as f:
        f.write("hello world")

    # upload the file
    s3client.upload_file("test.txt", bucket_name, "test4.txt")
    s3client.upload_file("test.txt", bucket_name, "test5.txt")

    # list the files in the bucket
    response = s3client.list_objects_v2(Bucket=bucket_name)
    for obj in response['Contents']:
        print("real response", obj['Key']) # should print "test.txt"

    # download the file
    s3client.download_file(bucket_name, "test4.txt", os_file_path+"/test3.txt")
    print(os_file_path+"/test3.txt")
    # check file content
    with open(os_file_path+"/test3.txt", "r") as f:
        print("real", f.read())  # should print "hello world"

    os.remove("test.txt")
    os.remove("test3.txt")
    response = s3client.list_objects_v2(Bucket=bucket_name)
    print(response)
    for obj in response['Contents']:
        print("real response", obj['Key']) # should print "test.txt"
        s3client.delete_object(Bucket=bucket_name, Key=obj['Key'])
    response = s3client.list_objects_v2(Bucket=bucket_name)
    print(response)

def test_hash():
    hash_result = hashlib.md5("test3.txt".encode())
    hash_result_hex_str = hash_result.hexdigest()
    hash_result_hex = int(hash_result_hex_str, 16)
    # printing the equivalent hexadecimal value.
    print("The hexadecimal equivalent of hash is : ", end ="")
    print(hash_result_hex)
    #print(type(hash_result_hex))
    print(hex(hash_result_hex))

#test_bucket()
provision_aws()
#test_hash()
#print(s3client)
#print(rds_client)

@manager.route('/')
def main():
    return render_template("main.html")

@manager.route('/upload', methods=['POST'])
def uploadImage():
    # upload image with key
    # transfer the bytes into dict
    data = request.form
    key = data.get('key')
    imageContent = data.get('file')
    value = base64.b64encode(str(imageContent).encode())
    imageSize = eval(imageContent).get('size')
    print(eval(imageContent).get('name'))
    requestJson = {
        'key': key,
        'value': value,
        'size': imageSize, 
        'name': eval(imageContent).get('name')
    }
    requests.post(memcache_pool_url + '/put', params=requestJson)
    filename  = request.args.get('name')
    full_file_path = os.path.join(os_file_path, filename)
    if os.path.isfile(full_file_path):
        os.remove(full_file_path)
    with open(full_file_path, 'wb') as fp:
        fp.write(value)
    s3client.upload_file(full_file_path, bucket_name, filename)
    
    # pending saving to rds
    if db.readFileInfo(key) == None:
        db.insertFileInfo(FILEINFO(key, filename, imageSize))
    else:
        db.updFileInfo(FILEINFO(key, filename, imageSize))
    
    resp = OrderedDict([("success", "true"), ("key", key)])
    response = manager.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )

    return response

@manager.route('/api/upload', methods=['POST'])
def upload_autotest():
    """
    Upload the key to the database
    Store the value as a file in the local file system, key as filename
    key: string
    value: string (For images, base64 encoded string)
    """
    key = request.form.get('key')
    image = request.files.get('file')
    imageBytes = image.read()
    imageSize = len(imageBytes)
    encodedImage = base64.b64encode(str(imageBytes).encode())
    requestJson = {
        'key': key,
        'value': encodedImage, 
        'size': imageSize
    }
    requests.post(memcache_pool_url + '/put', params=requestJson)
    value = encodedImage
    filename  = image.filename
    full_file_path = os.path.join(os_file_path, filename)
    if os.path.isfile(full_file_path):
        os.remove(full_file_path)
    with open(full_file_path, 'wb') as fp:
        fp.write(value)
    s3client.upload_file(full_file_path, bucket_name, filename)
    
    # pending saving to rds
    if db.readFileInfo(key) == None:
        db.insertFileInfo(FILEINFO(key, filename, imageSize))
    else:
        db.updFileInfo(FILEINFO(key, filename, imageSize))

    resp = OrderedDict([("success", "true"), ("key", key)])
    response = manager.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )

    return response

@manager.route('/getFromS3', methods=['POST'])
def getFromS3():
    """
    Fetch the value (file, or image) from the file system given a key
    key: string
    """
    key = request.args.get('key')

    #pending rds getting filename
    fileInfo = db.readFileInfo(key)
    filename = fileInfo.location
    fileSize = fileInfo.size
    checkFile = s3client.list_objects_v2(Bucket=bucket_name, Prefix=filename)
    if "Contents" in checkFile:
        full_file_path = os.path.join(os_file_path, filename)
        s3client.download_file(bucket_name, filename, full_file_path)
        value = Path(full_file_path).read_text()
        resp = {
            "success" : "true", 
            "value": value, 
            "size": fileSize
        }
        response = manager.response_class(
            response=json.dumps(resp),
            status=200,
            mimetype='application/json'
        )
    else:
        response = manager.response_class(
            response=json.dumps("File Not Found"),
            status=400,
            mimetype='application/json'
        )

    return response

@manager.route('/api/getImage', methods=['POST'])
def getImage():
    # retrieve image
    key = request.form.get('key')
    requestJson = {
        'key': key
    }
    res = requests.post(memcache_pool_url + '/getImage', params=requestJson)
    if res.status_code == 400:
        # cache misses, query AWS service
        print('cache misses, query AWS service')
        res = requests.post(manager_url + '/getFromS3', params=requestJson)
        if res.status_code == 400:
            resp = OrderedDict()
            resp["success"] = "false"
            resp["error"] = {
                "code": 400,
                "message": "Target file is not found because the given key is not found."
            }
            response = manager.response_class(
                response=json.dumps(resp),
                status=400,
                mimetype='application/json'
            )
        else:
            json_response = res.json()
            value = json_response["value"]
            size = json_response["size"]
            content = base64.b64decode(value)
            resp = OrderedDict()
            resp["success"] = "true"
            resp["key"] = key
            resp["content"] = bytes.decode(content)
            requestJson = {
                'key': key,
                'value': value, 
                'size': size
            }
            requests.post(memcache_pool_url + '/put', params=requestJson)
            response = manager.response_class(
                response=json.dumps(resp),
                status=200,
                mimetype='application/json'
            )
        return response
    else:
        print('cache success')
        json_response = res.json()
        value = json_response["value"]
        content = base64.b64decode(value)
        resp = OrderedDict()
        resp["success"] = "true"
        resp["key"] = key
        resp["content"] = bytes.decode(content)
        response = manager.response_class(
            response=json.dumps(resp),
            status=200,
            mimetype='application/json'
        )
        return response

@manager.route('/api/key/<key_value>', methods=['POST'])
def retrieve_autotest(key_value):
    # retrieve image
    requestJson = {
        'key': key_value
    }
    res = requests.post(memcache_pool_url + '/getImage', params=requestJson)
    if res.status_code == 400:
        # cache misses, query AWS service
        print('cache misses, query AWS service')
        res = requests.post(manager_url + '/getFromS3', params=requestJson)
        if res.status_code == 400:
            resp = OrderedDict()
            resp["success"] = "false"
            resp["error"] = {
                "code": 400,
                "message": "Target file is not found because the given key is not found."
            }
            response = manager.response_class(
                response=json.dumps(resp),
                status=400,
                mimetype='application/json'
            )
        else:
            json_response = res.json()
            value = json_response["value"]
            size = json_response["size"]
            content = base64.b64decode(value)
            resp = OrderedDict()
            resp["success"] = "true"
            resp["key"] = key_value
            resp["content"] = bytes.decode(content)
            requestJson = {
                'key': key_value,
                'value': value, 
                'size': size
            }
            requests.post(memcache_pool_url + '/put', params=requestJson)
            response = manager.response_class(
                response=json.dumps(resp),
                status=200,
                mimetype='application/json'
            )
        return response
    else:
        print('cache success')
        json_response = res.json()
        value = json_response["value"]
        content = base64.b64decode(value)
        resp = OrderedDict()
        resp["success"] = "true"
        resp["key"] = key_value
        resp["content"] = bytes.decode(content)
        response = manager.response_class(
            response=json.dumps(resp),
            status=200,
            mimetype='application/json'
        )
        return response

@manager.route('/api/delete_all', methods=['POST'])
def delete_all():
    """
    Remove all the key and values (files, images) from the database and filesystem
    No inputs required
    """
    response = s3client.list_objects_v2(Bucket=bucket_name)
    #print(response)
    if 'Contents' in response: 
        for obj in response['Contents']:
            s3client.delete_object(Bucket=bucket_name, Key=obj['Key'])
    #pending removal from rds
    db.delAllFileInfo()
    
    requests.post(memcache_pool_url + '/clear')
    resp = {
        "success" : "true"
    }
    response = manager.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response


@manager.route('/clear_memcache', methods=['POST'])
def clear_memcache():
    """
    Remove all the key and values (files, images) from the memcache
    No inputs required
    """
    requests.post(memcache_pool_url + '/clear')
    resp = {
        "success" : "true"
    }
    response = manager.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response

@manager.route('/api/configure_cache', methods=['GET', 'POST'])
def configure_memcache():

    print('args ->', request.args)

    requestJson = {}
    if 'mode' in request.args: 
        requestJson["mode"] = request.args.get('mode')
        if requestJson["mode"] != "manual" and requestJson["mode"] != "auto": 
            resp = {
                "success": "false",
                "error": {
                        "code": 400, 
                        "message": "Invalid Mode Configuration"
                        }
            }               
            response = manager.response_class(
                response=json.dumps(resp),
                status=400,
                mimetype='application/json'
            )
            return response
    if 'numNodes' in request.args: 
        requestJson["numNodes"] = int(request.args.get('numNodes'))
        if requestJson["numNodes"] > 8 or requestJson["numNodes"] < 1: 
            resp = {
                "success": "false",
                "error": {
                        "code": 400, 
                        "message": "Number of nodes must be between 1 and 8"
                        }
            }               
            response = manager.response_class(
                response=json.dumps(resp),
                status=400,
                mimetype='application/json'
            )
            return response
    if 'cacheSize' in request.args: 
        requestJson["cacheSize"] = int(request.args.get('cacheSize'))
    if 'policy' in request.args: 
        requestJson["policy"] = request.args.get('policy')
        if requestJson["policy"] != "LRU" and requestJson["policy"] != "RR": 
            resp = {
                "success": "false",
                "error": {
                        "code": 400, 
                        "message": "Invalid Mode Configuration"
                        }
            }               
            response = manager.response_class(
                response=json.dumps(resp),
                status=400,
                mimetype='application/json'
            )
            return response
    if 'expRatio' in request.args: 
        requestJson["expRatio"] = request.args.get('expRatio')
    if 'shrinkRatio' in request.args: 
        requestJson["shrinkRatio"] = request.args.get('shrinkRatio')
    if 'maxMiss' in request.args: 
        requestJson["maxMiss"] = request.args.get('maxMiss')
    if 'minMiss' in request.args: 
        requestJson["minMiss"] = request.args.get('minMiss')
    
    #Pending: if mode is auto specified, need to notify the auto scaler

    requests.post(memcache_pool_url + '/configure', params=requestJson)
    requests.post(autoscaler_url + '/autoScalarConfig', params=requestJson)
    resp = {"success": "true"}
    for key in requestJson:
        resp[key] = requestJson[key]
    response = manager.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response

@manager.route('/api/getNumNodes', methods=['POST'])
def getNumNodes_Manager():
    res = requests.post(memcache_pool_url + '/getNumNodes')
    print(res.content)
    json_response = res.json()
    numNodes = json_response["numNodes"]
    resp = {
        "success" : "true", 
        "numNodes": numNodes
    }
    response = manager.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response

@manager.route('/api/getRate', methods=['POST'])
def getRate():
    requestJson = {}
    if 'rate' in request.args:
        
        requestJson["rate"] = request.args.get('rate')
        
        if requestJson["rate"] != "miss" and requestJson["rate"] != "hit": 
            resp = {
                "success": "false",
                "error": {
                        "code": 400, 
                        "message": "Only miss and hit rates are available"
                        }
            }               
            response = manager.response_class(
                response=json.dumps(resp),
                status=400,
                mimetype='application/json'
            )
            return response
        
        # get stats from cloudwatch
        #cloudwatch = boto3.client('cloudwatch')
        cloudwatch = boto3.client( 'cloudwatch', 
                                  region_name='us-east-1', 
                                  aws_access_key_id = 'AKIAVW4WDBYWC5TM7LHC', 
                                  aws_secret_access_key = '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'
                                  )
        try:
            totalRequests = cloudwatch.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=1 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName='numTotalRequests',
                Namespace='Cache Stats',
                Unit='None',
                Statistics=['Sum'],
            )
        except IndexError:
            totalNum = 0
            print('the metric-totalNum is empty')
        else:
            totalNum = totalRequests['Datapoints'][0]['Sum']
            print("totalNum =", totalNum)
        try:
            missRequests = cloudwatch.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=1 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName='numMissRequests',
                Namespace='Cache Stats',
                Unit='None',
                Statistics=['Sum'],
            )
        except IndexError:
            missNum = 0
            print('the metric-missNum is empty')
        else:
            missNum = missRequests['Datapoints'][0]['Sum']
            print("missNum =", missNum)

        rate = 0.0
        if totalNum > 0:
            if requestJson["rate"] == "miss":
                rate = missNum / totalNum
            else:
                rate = (totalNum - missNum) / totalNum
        
        resp = {
            "success": "true",
            "rate": requestJson["rate"],
            "value": rate
        }
                 
        response = manager.response_class(
            response=json.dumps(resp),
            status=200,
            mimetype='application/json'
        )
        return response

    # When 'rate' is not found
    resp = {
        "success": "false",
        "error": {
            "code": 400, 
            "message": "Only miss and hit rates are available"
        }
    }               
    response = manager.response_class(
        response=json.dumps(resp),
        status=400,
        mimetype='application/json'
    )
    return response

@manager.route('/api/list_keys', methods=['POST'])
def list_keys():
    res = requests.post(memcache_pool_url + '/all_keys')
    json_response = res.json()
    print(json_response)
    all_keys = json_response["all_keys"]
    resp = {
        "success" : "true", 
        "keys": all_keys
    }
    response = manager.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response

@manager.route('/allKeyDB', methods=['POST'])
def allKeyDB():
    """
    Display all the keys that stored in the database
    No inputs required
    """
    allKeys = db.readAllFileKeys()

    response = manager.response_class(
        response=json.dumps(allKeys),
        status=200,
        mimetype='application/json'
    )

    return response

#####################################
##    Manager Front End Routes     ##
#####################################
@manager.route('/displayCharts', methods=['GET', 'POST'])
def displayCharts():
    
    cloudwatch = boto3.client(
        'cloudwatch',
        region_name='us-east-1',
        aws_access_key_id = 'AKIAVW4WDBYWC5TM7LHC',
        aws_secret_access_key = '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'
    )
    
    def sort_by_timeStamp(datapoint):
        return datapoint['Timestamp']

    # get numActiveNodes list
    resp1 = cloudwatch.get_metric_statistics(
        Period     = 1*60,
        StartTime  = datetime.utcnow() - timedelta(seconds=30*60),
        EndTime    = datetime.utcnow(),
        MetricName = 'numActiveNodes',
        Namespace  = 'Cache Stats',
        Unit       = 'None',
        Statistics = ['Sum', 'Minimum', 'Maximum', 'Average', 'SampleCount']        
    )
    sortedResp1 = sorted(resp1['Datapoints'], key=sort_by_timeStamp)
    numActiveNodesList = [datapoint['Maximum'] for datapoint in sortedResp1]

    # get numTotalRequests list
    resp2 = cloudwatch.get_metric_statistics(
        Period     = 1*60,
        StartTime  = datetime.utcnow() - timedelta(seconds=30*60),
        EndTime    = datetime.utcnow(),
        MetricName = 'numTotalRequests',
        Namespace  = 'Cache Stats',
        Unit       = 'None',
        Statistics = ['Sum', 'Minimum', 'Maximum', 'Average', 'SampleCount']
    )
    sortedResp2 = sorted(resp2['Datapoints'], key=sort_by_timeStamp)
    numTotalRequestsList = [datapoint['Sum'] for datapoint in sortedResp2]

    # get numMissRequests list
    resp3 = cloudwatch.get_metric_statistics(
        Period     = 1*60,
        StartTime  = datetime.utcnow() - timedelta(seconds=30*60),
        EndTime    = datetime.utcnow(),
        MetricName = 'numMissRequests',
        Namespace  = 'Cache Stats',
        Unit       = 'None',
        Statistics = ['Sum', 'Minimum', 'Maximum', 'Average', 'SampleCount'] 
    )
    sortedResp3 = sorted(resp3['Datapoints'], key=sort_by_timeStamp)
    numMissRequestsList = [datapoint['Sum'] for datapoint in sortedResp3]

    # get numItems list
    resp4 = cloudwatch.get_metric_statistics(
        Period     = 1*60,
        StartTime  = datetime.utcnow() - timedelta(seconds=30*60),
        EndTime    = datetime.utcnow(),
        MetricName = 'numItems',
        Namespace  = 'Cache Stats',
        Unit       = 'None',
        Statistics = ['Sum', 'Minimum', 'Maximum', 'Average', 'SampleCount']      
    )
    sortedResp4 = sorted(resp4['Datapoints'], key=sort_by_timeStamp)
    numItemsList = [datapoint['Maximum'] for datapoint in sortedResp4]

    # get totalSize list
    resp5 = cloudwatch.get_metric_statistics(
        Period     = 1*60,
        StartTime  = datetime.utcnow() - timedelta(seconds=30*60),
        EndTime    = datetime.utcnow(),
        MetricName = 'totalSize',
        Namespace  = 'Cache Stats',
        Unit       = 'None',
        Statistics = ['Sum', 'Minimum', 'Maximum', 'Average', 'SampleCount']      
    )
    sortedResp5 = sorted(resp5['Datapoints'], key=sort_by_timeStamp)
    totalSizeList = [datapoint['Maximum'] for datapoint in sortedResp5]


    missRateList      = [ (numMissRequestsList[i] / numTotalRequestsList[i]) if numTotalRequestsList[i]>0 else 0.0 for i in range(len(numTotalRequestsList))]
    hitRateList       = [ (numTotalRequestsList[i] - numMissRequestsList[i] / numTotalRequestsList[i]) if numTotalRequestsList[i]>0 else 0.0 for i in range(len(numTotalRequestsList))]

    # print('---------------------- resp1 ------------------------')
    # for datapoint in sortedResp1:
    #     print(datapoint)
    # print(len(sortedResp1))

    # print('---------------------- resp2 ------------------------')
    # for datapoint in sortedResp2:
    #     print(datapoint)
    # print(len(sortedResp2))

    # Create a list to store the Plotly chart objects
    figs = []
    # x = [datetime.now(pytz.timezone('America/Toronto'))]
    # for i in range(29):
    #     x.append(x[-1] - timedelta(seconds=60))
    x_data = [
        [datapoint['Timestamp'] for datapoint in sortedResp1],
        [datapoint['Timestamp'] for datapoint in sortedResp2],
        [datapoint['Timestamp'] for datapoint in sortedResp2],
        [datapoint['Timestamp'] for datapoint in sortedResp4],
        [datapoint['Timestamp'] for datapoint in sortedResp5],
        [datapoint['Timestamp'] for datapoint in sortedResp2]
    ]
    x_label = 'Time'
    y_data = [
        numActiveNodesList,
        missRateList,
        hitRateList,
        numItemsList,
        totalSizeList,
        numTotalRequestsList
    ]
    chart_names = [
        'Number of active nodes',
        'Miss Rates', 
        'Hit Rates', 
        'Total number of cache items', 
        'Total size of cache items (MB)', 
        'Number of requests'
    ]

    # Create a Plotly line chart for each set of x and y data
    for x, y, name in zip(x_data, y_data, chart_names):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name=name))
        if name == 'Miss Rates' or name == 'Hit Rates':
            fig.update_layout(
                title=name, 
                xaxis_title=x_label, 
                yaxis_title=name,
                yaxis=dict(
                    range=[0.0, 1.0] 
                ),
                width=800, 
                height=500)
        elif name == 'Number of active nodes':
            fig.update_layout(
                title=name, 
                xaxis_title=x_label, 
                yaxis_title=name,
                yaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=1,
                    range=[0, 8] 
                ),
                width=800, 
                height=500)
        elif name == 'Total number of cache items' or name == "Number of requests":
            fig.update_layout(
                title=name,
                xaxis_title=x_label,
                yaxis_title=name,
                yaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=1
                ),
                width=800, 
                height=500)            
        else:
            fig.update_layout(
                title=name,
                xaxis_title=x_label,
                yaxis_title=name,
                width=800,
                height=500)
        figs.append(fig)

    # Generate the HTML for each chart using Plotly's to_html() method
    chart_html = []
    for fig in figs:
        chart_html.append(fig.to_html(full_html=False, include_plotlyjs=False))

    # Wrap the HTML for each chart in a <div> tag with a unique ID
    chart_divs = ['''
        <head>
            <title>Charts</title>
            <!-- Load Bootstrap CSS -->
            <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
            <!-- Bootstrap JS and jQuery -->
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
            <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                .navbar-vertical {
                    background-color: #f8f8f8;
                    border: 1px solid #ddd;
                    padding: 20px;
                    position: fixed;
                    top: 0;
                    bottom: 0;
                    left: 0;
                    width: 200px;
                    overflow-y: auto;
                }
                .navbar-vertical .navbar-brand {
                    font-weight: bold;
                    font-size: 20px;
                    margin-bottom: 20px;
                }
                .navbar-vertical .nav {
                    margin-top: 20px;
                }
                .navbar-vertical .nav > li > a {
                    padding: 10px 15px;
                    font-size: 16px;
                }
                .navbar-vertical .nav > li > a:hover {
                    background-color: #ddd;
                }
                nav a.active {
                    color: #fff;
                    background-color: #337ab7;
                }                
                .config {
                    padding-left: 210px;
                }
            </style>
        </head>
        <body>
            <nav class="navbar navbar-vertical">
                <div class="navbar-header">
                    <a class="navbar-brand" href="/">Manager UI</a>
                </div>
                <ul class="nav navbar-nav">
                    <li><a href="/displayCharts" class="active">Display Charts</a></li>
                    <li><a href="/configureCache">Configure Cache</a></li>
                    <li><a href="/configureCachePoolSizingMode">Configure Pool</a></li>
                    <li><a href="/deletes">Clear Data</a></li>
                </ul>
            </nav>
        </body>
    ''']
    for i, html in enumerate(chart_html):
        chart_divs.append(f'<div class="config" id="chart{i+1}">{html}</div>')

    # Combine the chart <div> tags into a single HTML string
    html = ''.join(chart_divs)

    # Return the HTML string
    return html

@manager.route('/configureCache', methods=['GET', 'POST'])
def configureCache():
    return render_template('configureCache.html')

@manager.route('/configureCachePoolSizingMode', methods=['GET', 'POST'])
def configureCachePoolSizingMode():
    res = requests.post(memcache_pool_url + '/getNumNodes')
    json_response = res.json()
    numNodes = int(json_response["numNodes"])
    #numNodes = 1
    return render_template('configureCachePoolSizingMode.html', numNodes = numNodes)

@manager.route('/deletes', methods=['GET', 'POST'])
def deletes():
    return render_template('deletes.html')

@manager.route('/deleteAllData', methods=['GET', 'POST'])
def deleteAllData():
    requests.post(manager_url + '/api/delete_all')
    return manager.response_class(
        response=json.dumps('ok'),
        status=200,
        mimetype='application/json'
    )

@manager.route('/clearCache', methods=['GET', 'POST'])
def clearCache():
    requests.post(memcache_pool_url + '/clear')
    return manager.response_class(
        response=json.dumps('ok'),
        status=200,
        mimetype='application/json'
    )