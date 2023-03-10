from flask import render_template, url_for, request
import boto3
from datetime import datetime, timedelta
import sched
import time
from main import webapp
from ..app import autoScaler
import requests

cloudwatch = boto3.client('cloudwatch')
manager_url = 'http://127.0.0.1:5000'
memcache_pool_url = 'http://127.0.0.1:5002'
autoscaler_url = 'http://127.0.0.1:5003'

# TODO：这些配置信息应该是danny在写的时候会设置的 我需要知道
missRateConfig = {
    'metricName': '',
    'namespace': '',
    'statistics': 'Average',
    'unit': 'None',
    'dimensions': [{
        'Name': '',
        'Value': ''
    }]
}
thresholdAndRatio = {
    'max': 8,
    'min': 1,
    'expandRatio': 2,
    'shrinkRatio': 0.5
}
poolConfig = {
    'size': 2,
}
mode = 'auto'

@autoScaler.route('/', methods = ['GET'])
def hello():
    return 'hello,world'

#TODO：路径分配
@autoScaler.route('/autoScalarConfig', methods = ['POST'])
def autoScalarConfig():
    #config = request.args.get('config')
    config = {}
    #TODO:对missRateConfig的写入
    operateMode = config.get('mode')
    global mode
    if operateMode == 'manual':
        mode = 'manual'
    elif operateMode == 'auto':
        mode = 'auto'

# Monitor miss rate through AWS CloudWatch API(every 1 minute)
# If the missRate is lower or higher than the min or max threshold, call resizeMemPool func
def monitorMissRate():
    missRate = cloudwatch.get_metric_statistics(
        Period=1 * 60,  # get the missRate of last 1 minute
        StartTime=datetime.utcnow() - timedelta(seconds=1 * 60),
        EndTime=datetime.utcnow(),
        MetricName=missRateConfig.get('metricName'),
        Namespace=missRateConfig.get('namespace'),
        Unit=missRateConfig.get('unit'),
        Statistics=[missRateConfig.get('statistics')],
        Dimensions=missRateConfig.get('dimensions')
    )
    if missRate > thresholdAndRatio.get('max'):
        print('the missRate', missRate, 'is higher than the max threshold', thresholdAndRatio.get('max'))
        resizeMemPool(thresholdAndRatio.get('expandRatio'))
    if missRate < thresholdAndRatio.get('min'):
        print('the missRate', missRate, ' is lower than the min threshold', thresholdAndRatio.get('min'))
        resizeMemPool(thresholdAndRatio.get('shrinkRatio'))


# Resize mem-cache pool
def resizeMemPool(resizeRatio: float):
    """
    :param resizeRatio
    :return: None
    """
    print('Beginning changing the pool size by ratio', resizeRatio)
    size = poolConfig.get('size') * resizeRatio
    if size > thresholdAndRatio.get('max') or size < thresholdAndRatio.get('min'):
        print('can not change the pool size, because it already hit the threshold')
    else:
        # TODO: 回写size到pool的配置中，这个看是单独命名一个config文件，大家统一从里面操作？
        if resizeRatio > 1:
            requestJson = {
                'change': 'grow'
            }
            requests.post(memcache_pool_url + '/auto_change', params=requestJson)
        else:
            requestJson = {
                'change': 'shrink'
            }
            requests.post(memcache_pool_url + '/auto_change', params=requestJson)


s = sched.scheduler(time.time, time.sleep)


# run the monitor function every 60 seconds
def perform(inc):
    s.enter(inc, 0, perform, (inc,))
    monitorMissRate()


def main(inc=60):
    if mode == 'auto':
        s.enter(0, 0, perform, (inc,))
        s.run()

#
# if __name__ == '__main__':
#     main()
