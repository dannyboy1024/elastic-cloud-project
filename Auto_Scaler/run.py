#!../venv/bin/python
from app import autoScaler
import boto3
from datetime import datetime, timedelta
import sched
import time
from flask import request, json
import requests

memcache_pool_url = 'http://127.0.0.1:5002'

cloudwatch = boto3.client('cloudwatch')
thresholdAndRatio = {
    'max': 0.8,
    'min': 0.2
}
mode = 'manual'

scheduler = sched.scheduler(time.time, time.sleep)


# run the monitor function every 60 seconds
def monitor(inc):
    if mode == 'auto':
        monitorMissRate()
        scheduler.enter(inc, 0, monitor, (inc,))



@autoScaler.route('/autoScalarConfig', methods=['POST'])
def autoScalarConfig():
    global mode
    if 'mode' in request.args:
        operateMode = request.args.get('mode')
        if operateMode == 'manual':
            mode = 'manual'
        elif operateMode == 'auto':
            mode = 'auto'
            scheduler.enter(0, 0, monitor, (60,))
            scheduler.run()
    global thresholdAndRatio
    if 'maxMiss' in request.args:
        arg_ratio = request.args.get('maxMiss')
        if arg_ratio != "": 
            maxMiss = float(arg_ratio)
            thresholdAndRatio['max'] = maxMiss
    if 'minMiss' in request.args:
        arg_ratio = request.args.get('minMiss')
        if arg_ratio != "": 
            minMiss = float(arg_ratio)
            thresholdAndRatio['min'] = minMiss
    resp = {
        "success" : "true"
    }
    response = autoScaler.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )
    return response


# Monitor miss rate through AWS CloudWatch API(every 1 minute)
# If the missRate is lower or higher than the min or max threshold, call resizeMemPool func
def monitorMissRate():
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
        totalNum = totalRequests['Datapoints'][0]['Sum']

        missRequests = cloudwatch.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.utcnow() - timedelta(seconds=1 * 60),
            EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName='numMissRequests',
            Namespace='Cache Stats',
            Unit='None',
            Statistics=['Sum'],
        )
        MissNum = missRequests['Datapoints'][0]['Sum']
    except IndexError:
        print('the metric is empty')
    else:
        missRate = MissNum / totalNum
        if missRate > thresholdAndRatio.get('max'):
            print('the missRate', missRate, 'is higher than the max threshold', thresholdAndRatio.get('max'))
            requests.post(memcache_pool_url + '/auto_change', params={'change': 'grow'})
        if missRate < thresholdAndRatio.get('min'):
            print('the missRate', missRate, ' is lower than the min threshold', thresholdAndRatio.get('min'))
            requests.post(memcache_pool_url + '/auto_change', params={'change': 'shrink'})


autoScaler.run('0.0.0.0', 5003, debug=False)
