
from flask import render_template, url_for, request
from app import manager, db, FILEINFO
from flask import json
from collections import OrderedDict
import boto3
from moto import mock_s3
from pathlib import Path
import os
import hashlib
import base64
import requests
import plotly.graph_objs as go

os_file_path = os.getcwd()
bucket_name = 'ece1779-winter23-a2-bucket'
manager_url = 'http://127.0.0.1:5000'
memcache_pool_url = 'http://127.0.0.1:5002'
autoscaler_url = 'http://127.0.0.1:5003'
s3client = None
rds_client = None

def provision_aws():
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
test_hash()

@manager.route('/')
def main():
    return render_template("main.html")

@manager.route('/api/upload', methods=['POST'])
def upload():
    """
    Upload the key to the database
    Store the value as a file in the local file system, key as filename
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
    requests.post(memcache_pool_url + '/put', params=requestJson)
    value = encodedImage
    filename  = request.args.get('name')
    full_file_path = os.path.join(os_file_path, filename)
    if os.path.isfile(full_file_path):
        os.remove(full_file_path)
    with open(full_file_path, 'w') as fp:
        fp.write(value)
    s3client.upload_file(full_file_path, bucket_name, filename)
    
    # pending saving to rds
    if db.readFileInfo(key) == None:
        db.insertFileInfo(FILEINFO(key, full_file_path))
    else:
        db.updFileInfo(FILEINFO(key, full_file_path))
    

    response = manager.response_class(
        response=json.dumps(full_file_path),
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

    filename = request.args.get('name')
    full_file_path = os.path.join(os_file_path, filename)

    s3client.download_file(bucket_name, filename, full_file_path)
    fileInfo = None
    if fileInfo == None:
        response = manager.response_class(
            response=json.dumps("File Not Found"),
            status=400,
            mimetype='application/json'
        )
    else:
        full_file_path = fileInfo.location
        value = Path(full_file_path).read_text()
        response = manager.response_class(
            response=json.dumps(value),
            status=200,
            mimetype='application/json'
        )

    return response

@manager.route('/api/key/<key_value>', methods=['POST'])
def retrieve(key_value):
    # retrieve image
    requestJson = {
        'key': key_value
    }
    res = requests.post(memcache_pool_url + '/key/<key_value>', params=requestJson)
    if res.status_code == 400:
        # cache misses or do not use cache, query db
        print('cache misses or cache not used, query db')
        res = requests.post(manager_url + '/getFromS3', params=requestJson)
        if res.status_code == 400:
            resp = OrderedDict()
            resp["success"] = "false"
            resp["error"] = {
                "code": 400,
                "message": "Target file is not found because the given key is not found in database."
            }
            response = manager.response_class(
                response=json.dumps(resp),
                status=200,
                mimetype='application/json'
            )
        else:
            content = base64.b64decode(res.content)
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
    else:
        print('cache success')
        content = base64.b64decode(res.content)
        resp = OrderedDict()
        resp["success"] = "true"
        resp["key"] = key_value
        resp["content"] = bytes.decode(content)
        response = application.response_class(
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
    Remove all the key and values (files, images) from the database and filesystem
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

@manager.route('/api/configure_cache', methods=['POST'])
def configure_memcache():
    pass

@manager.route('/api/getNumNodes', methods=['POST'])
def getNumNodes_Manager():
    res = requests.post(memcache_pool_url + '/getNumNodes')
    numNodes = res.content
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
    pass

@manager.route('/api/list_keys', methods=['POST'])
def list_keys():
    res = requests.post(memcache_pool_url + '/all_keys')
    all_keys = res.content
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

#####################################
##    Manager Front end routes     ##
#####################################
@manager.route('/displayCharts', methods=['GET'])
def displayCharts():
    
    # TODO: get stats from cloudwatch. Hardcoded so far #
    missRates = [0.5 for i in range(30)]
    hitRates = [0.5 for i in range(30)]
    totalNumCacheItems = [i for i in range(30)]
    totalSizeCacheItems = [i * 1024 * 1024 for i in range(30)]
    numRequestsServedPerMinute = [1 for i in range(30)]

    # Create a list to store the Plotly chart objects
    figs = []
    x = [i for i in range(30)]
    x_label = 'Time (Minutes)'
    y_data = [missRates, hitRates, totalNumCacheItems, totalSizeCacheItems, numRequestsServedPerMinute]
    chart_names = ['Miss Rates', 
                   'Hit Rates', 
                   'Total number of cache items', 
                   'Total size of cache items', 
                   'Number of requests / minute'
                   ]

    # Create a Plotly line chart for each set of x and y data
    for y, name in zip(y_data, chart_names):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name=name))
        fig.update_layout(title=name, xaxis_title=x_label, yaxis_title=name, width=800, height=500)
        figs.append(fig)

    # Generate the HTML for each chart using Plotly's to_html() method
    chart_html = []
    for fig in figs:
        chart_html.append(fig.to_html(full_html=False, include_plotlyjs=False))

    # Wrap the HTML for each chart in a <div> tag with a unique ID
    chart_divs = ['''
        <head>
            <title>Line Chart Example</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
    ''']
    for i, html in enumerate(chart_html):
        chart_divs.append(f'<div id="chart{i+1}">{html}</div>')

    # Combine the chart <div> tags into a single HTML string
    html = ''.join(chart_divs)

    # Return the HTML string
    return html

@manager.route('/configureCache', methods=['GET', 'POST'])
def configureCache():
    policies = ['Random Replacement', 'Least Recently Used']
    return render_template('configureCache.html', policies=policies)

@manager.route('/configureCachePoolSizingMode', methods=['GET', 'POST'])
def configureCachePoolSizingMode():
    dropdown_choices = ['Option 1', 'Option 2']
    selected_option = None
    show_inputs = False

    if request.method == 'POST':
        selected_option = request.form['configureCachePoolSizingMode']
        show_inputs = (request.form['configureCachePoolSizingMode'] == 'Option 2')

    return render_template('configureCachePoolSizingMode.html', dropdown_choices=dropdown_choices, selected_option=selected_option, show_inputs=show_inputs)

@manager.route('/deleteAllData', methods=['GET', 'POST'])
def deleteAllData():
    ## delete all data ##
    return

@manager.route('/clearCache', methods=['POST'])
def clearCache():
    ## clear cache ##
    return
