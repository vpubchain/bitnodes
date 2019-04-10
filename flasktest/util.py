#!/usr/bin/env python

import os
import sys
import time
import json
import redis
import hashlib
import urllib
import urllib2
import json
from ipaddress import ip_network

EXPORT_PATH="/var/www/bitnodes/bitnodes/data/export"
CRAWL_PATH="/var/www/bitnodes/bitnodes/data/crawl"
LIST_SNAPSHOTS_URL="https://vpubchain.net/api/v1/snapshots/"
locations={}

def get_location(x, y):
    global location
    key = bytes(x) + bytes(y)
    if (locations.has_key(key)):
        return locations[key]
  
    url = 'http://api.map.baidu.com/geocoder/v2/?ak=efaf6IBwbYlyR9UGQlugSAqIIOWLcDoK&location=' + bytes(x) + ',' + bytes(y) + '&output=json&pois=1';
    req = urllib2.Request(url)
    res_data = urllib2.urlopen(req)
    res = json.loads(res_data.read())
    #json = demjson.decode(res)
    #json = json.dumps(res)
    #print res 
    city = res["result"]["addressComponent"]["city"]
    country = res["result"]["addressComponent"]["country"]
    location = {}
    location["city"] = city
    location["country"] = country
    locations[key] = location
    return location

def new_redis_conn(db=0):
    """
    Returns new instance of Redis connection with the right db selected.
    """
    socket = os.environ.get('REDIS_SOCKET', "/run/redis/redis.sock")
    password = os.environ.get('REDIS_PASSWORD', None)
    return redis.StrictRedis(db=db, password=password, unix_socket_path=socket)


def get_keys(redis_conn, pattern, count=500):
    """
    Returns Redis keys matching pattern by iterating the keys space.
    """
    keys = []
    cursor = 0
    while True:
        (cursor, partial_keys) = redis_conn.scan(cursor, pattern, count)
        keys.extend(partial_keys)
        if cursor == 0:
            break
    return keys


def ip_to_network(address, prefix):
    """
    Returns CIDR notation to represent the address and its prefix.
    """
    network = ip_network(unicode("{}/{}".format(address, prefix)),
                         strict=False)
    return "{}/{}".format(network.network_address, prefix)


def get_all_nodes(work_path):
    results=[]
    json_list=sorted(os.listdir(work_path),reverse=True)
    json_nums=len(json_list)
    if json_nums==0:
        return result
    
    count=0
    for i in range(json_nums):
        json_name=work_path+'/'+json_list[i]
        if os.path.isfile(json_name):
            file_times,ext=json_list[i].split(".")
            try:
                file_time=int(file_times)
            except Exception,ex:
                continue
            count=count+1

            f=open(json_name, 'r')
            datastore = json.load(f)
            f.close()
            
            nodes={}
            height=0
            node_nums=0
            for data in datastore:
                data_len=len(data)
                if data_len!=4:
                    continue
                node_nums=node_nums+1
                if height<data[3]:
                    height=data[3]
            nodes["url"]=LIST_SNAPSHOTS_URL+file_times+"/"
            nodes["timestamp"]=file_time
            nodes["total_nodes"]=node_nums
            nodes["latest_height"]=height
        results.append(nodes)
    return count,results
      
def search_file(work_path,snapshot_time):       
    search_time=None
    next_time=None
    previous_name=None
    search_time=0
    file_name=""
    json_list=sorted(os.listdir(work_path), reverse=True)
    json_nums=len(json_list)
    if json_nums==0:
        return search_name,search_time,next_time,previous_time

    for i in range(json_nums):
        json_name=work_path+'/'+json_list[i]
        if os.path.isfile(json_name):
            file_size = os.path.getsize(json_name)
            file_times,ext=json_list[i].split(".")
            try:
                file_time=int(file_times)
            except Exception,ex:
                continue
            
            if snapshot_time>=file_time and file_size>2:
                search_name=json_name
                search_time=file_time
                
                if i==json_nums-1:
                    if i>0:
                        next_time,ext=json_list[i-1].split(".")
                    else:
                        next_time=None                        
                    previous_time=None                
                else:
                    previous_time,ext=json_list[i+1].split('.')
                    if i==0:
                        next_time=None
                    else:
                        next_time,ext=json_list[i-1].split('.')                                    
                break;
            else:
                if i==json_nums-1 and file_size>2:
                    search_name=json_name
                    search_time=file_time
                    if i>0:
                        next_time,ext=json_list[i-1].split('.')
                    else:
                        next_time=None                        
                    previous_time=None
    return search_name,search_time,next_time,previous_time

def search_node_from_address(address,port):
    address_port=address+":"+str(port)
    nodes={}
    json_list=sorted(os.listdir(EXPORT_PATH), reverse=True)
    json_nums=len(json_list)
    if json_nums==0:
        return nodes

    for i in range(json_nums):
        json_name=EXPORT_PATH+'/'+json_list[i]
        if os.path.isfile(json_name):
            file_times,ext=json_list[i].split(".")
            try:
                file_time=int(file_times)
            except Exception,ex:
                continue

            f=open(json_name, 'r')
            datastore = json.load(f)
            f.close()
            
            for data in datastore:
                data_len=len(data)
                if data_len!=15:
                    continue;
                list1=[]
                key=""
                key=data[0].encode('utf8')+":"+str(data[1])
                if key==address_port:
                    for i in range(data_len-2):
                        list1.append(data[i+2])
                    nodes[key]=list1
                    break
            
    return nodes

def  get_field(args):    
    fields=["protocol_version","user_agent","connected_since","services","height",
            "hostname","city","country_code","coordinates","timezone","asn","organization_name"]
    i=0
    for field in fields:
        if field==args:
            return True,i
        i=i+1
    return False,i

def  get_node_rtt_from_redis(redis_conn,address_port):   
    return redis_conn.lrange('rtt:{}'.formate(address_port),0,-1)    

def  get_inv_hash_from_redis(redis_conn,inv_hash):   
    return redis_conn.zrevrange('inv:2:{}'.format(inv_hash),0,-1,withscores=True)    

def find_node_from_redis(redis_conn,address,port):   
    nodes=redis_conn.smembers('up')  
    for node in nodes:
        (address1, port1, services) = node[5:].split("-", 2)
        if address==address1 and port==port1:
            return True
    return False
        

def get_nodes_hash_from_redis(redis_conn):   
    nodes_hash={}
    
    nodes=get_keys(redis_conn,'height:*')    
    for node in nodes:
        (address, port, services) = node[7:].split("-", 2)
        address_port=address+"-"+str(port)
        nodes_hash[hashlib.sha256(address_port).hexdigest()[:8]]=address_port
    
    """
    nodes=redis_conn.smembers('up')    
    for node in nodes:
        (address, port, services) = node[5:].split("-", 2)
        address_port=address+"-"+str(port)
        nodes_hash[hashlib.sha256(address_port).hexdigest()[:8]]=address_port
    """
    
    return nodes_hash        

def dict_slice(adict, start, end):
    keys = adict.keys()
    dict_slice = {}
    for k in keys[start:end]:
        dict_slice[k] = adict[k]
    return dict_slice

def find_nodes_by_field(nodes,q):    
    results={}
    nums=0
    for node in nodes :        
        agent=nodes[node]
        for item in agent:            
            if isinstance (item,unicode):
                if item.find(q)>=0:
            #if q in agent:
                    nums=nums+1
                    results[node]=agent
    return results,nums

if  __name__ == '__main__':
    sys.exit(search_node_from_address("47.104.25.28:9900"))
