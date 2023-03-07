import hashlib
import boto3
from flask import Flask
from flask_cors import CORS
import requests

ec2_resource = None

def check_partition(key):
    hash_result = hashlib.md5(key.encode())
    hash_result_hex_str = hash_result.hexdigest()
    hash_result_hex = int(hash_result_hex_str, 16)
    if hash_result_hex <= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 0
    elif hash_result_hex <= 0x1FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 1
    elif hash_result_hex <= 0x2FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 2
    elif hash_result_hex <= 0x3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 3
    elif hash_result_hex <= 0x4FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 4
    elif hash_result_hex <= 0x5FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 5
    elif hash_result_hex <= 0x6FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 6
    elif hash_result_hex <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 7
    elif hash_result_hex <= 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 8
    elif hash_result_hex <= 0x9FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 9
    elif hash_result_hex <= 0xAFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 10
    elif hash_result_hex <= 0xBFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 11
    elif hash_result_hex <= 0xCFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 12
    elif hash_result_hex <= 0xDFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 13
    elif hash_result_hex <= 0xEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 14
    elif hash_result_hex <= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
        return 15

def provision_ec2():
    ec2_resource = boto3.resource('ec2', region_name='us-east-1')
    for instance in ec2_resource.instances.all():
        if instance.id == 'i-07398e72531441a21':
            print("found skipped instance")
            continue
        memcache_pool_tracker.available_instances.append(instance.id)
        memcache_pool_tracker.instances_ip[instance.id] = instance.public_ip_address
        print(instance.id, " ", memcache_pool_tracker.instances_ip[instance.id])
    first_active_instance = memcache_pool_tracker.available_instances[0]
    memcache_pool_tracker.active_instances[first_active_instance] = memcache_pool_tracker.instances_ip[first_active_instance]


class memcache_pool_tracking:
    def __init__(self):
        self.num_active_instances = 1 
        self.available_instances = []
        self.instances_ip = {}
        self.active_instances = {}
        self.all_keys_with_node = {}
        self.scaling_mode = "manual"
        self.auto_expand = 2.0
        self.auto_shrink = 0.5
        self.total_size = 0
        self.num_items = 0
    
    def rebalance_nodes(self): 
        for key in self.all_keys_with_node:
            cache_partition = check_partition(key)
            node_num = cache_partition % self.num_active_instances
            if node_num != self.all_keys_with_node[key]:
                old_node_num = self.all_keys_with_node[key]
                old_node_instance = self.available_instances[old_node_num]
                old_node_ip = self.instances_ip[old_node_instance]
                old_url = 'http://'+str(old_node_ip)+':5000'
                requestJson = {
                    'key': key
                }
                res = requests.post(old_url + '/get', params=requestJson)
                if res.status_code == 400:
                    self.all_keys_with_node[key] = -1
                else: 
                    content = res.content
                    self.all_keys_with_node[key] = node_num
                    new_node_instance = self.available_instances[node_num]
                    new_node_ip = self.instances_ip[new_node_instance]
                    new_url = 'http://'+str(new_node_ip)+':5000'
                    requestJson = {
                        'key': key,
                        'value': content
                    }
                    requests.post(new_url + '/put', params=requestJson)
        keys_list = self.all_keys_with_node.keys()
        for key in keys_list:
            if self.all_keys_with_node[key] == -1:
                del self.all_keys_with_node[key]

    def manual_change(self, change):
        self.scaling_mode = "manual"
        if change == "grow" and self.num_active_instances < 8:
            new_index = self.num_active_instances
            new_instance = self.available_instances[new_index]
            self.active_instances[new_instance] = self.instances_ip[new_instance]
            self.num_active_instances += 1
            self.rebalance_nodes()
        elif change == "shrink" and self.num_active_instances > 1:
            shrink_index = self.num_active_instances - 1
            shrink_instance = self.available_instances[shrink_index]
            del self.active_instances[shrink_instance]
            self.num_active_instances -= 1
            self.rebalance_nodes()
    
    def auto_change(self, change): 
        self.scaling_mode = "auto"
        if change == "grow" and self.num_active_instances < 8:
            new_num_instance = int(self.num_active_instances * self.auto_expand)
            if new_num_instance != self.num_active_instances:
                if new_num_instance >= 8:
                    new_num_instance = 8
                for instance_num in range(new_num_instance-self.num_active_instances):
                    new_index = self.num_active_instances + instance_num
                    new_instance = self.available_instances[new_index]
                    self.active_instances[new_instance] = self.instances_ip[new_instance]
                self.num_active_instances = new_num_instance
                self.rebalance_nodes()
        elif change == "shrink" and self.num_active_instances > 1:
            new_num_instance = int(self.num_active_instances * self.auto_shrink)
            if new_num_instance != self.num_active_instances:
                if new_num_instance <= 1:
                    new_num_instance = 1
                for instance_num in range(self.num_active_instances-new_num_instance):
                    shrink_index = self.num_active_instances - 1 - instance_num
                    shrink_instance = self.available_instances[shrink_index]
                    del self.active_instances[shrink_instance]
                self.num_active_instances = new_num_instance
                self.rebalance_nodes()



memcachePool = Flask(__name__)
CORS(memcachePool)
memcache_pool_tracker = memcache_pool_tracking()
from app import main




