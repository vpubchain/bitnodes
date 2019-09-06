#!/usr/bin/env python
from flask import Flask, jsonify
from flask import abort

from flask import make_response
from flask import request

from flask_restful import reqparse

from flask_cors import CORS

import redis
import redis.connection

import os
import sys
import time
import json
import numpy

from binascii import hexlify, unhexlify
from ConfigParser import ConfigParser

import util
from util import get_location, new_redis_conn, get_keys, ip_to_network

REDIS_CONN = None
CONF = {}

app = Flask(__name__)

EXPORT_PATH="/var/www/bitnodes/data/export"
CRAWL_PATH="/var/www/bitnodes/data/crawl"
LIST_SNAPSHOTS_URL="https://vpubchain.net/api/v1.0/snapshots/"

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(504)
def params_eroor(error):
    return make_response(jsonify({'error': 'params error'}), 504)

@app.route('/vpbitnodes/api/v1.0/snapshots/', methods=['GET'])
def list_nodes_from_crawl():
    page_per=10000
    parser = reqparse.RequestParser()
    parser.add_argument('page',help='current page')
    args = parser.parse_args()   
    page=args['page']
    
    count,results=util.get_all_nodes(CRAWL_PATH)
    list_nodes={}
    if count==0:
        return jsonify({'details': 'Not found'})
    else:
        if page is None:
            page=1
        else:
            page=int(page)
        
        maxpage=(count+page_per-1)/page_per
        if page>maxpage:
            return jsonify({'details': 'Not found'})
        
        if page==0:
            page=1
                    
        list_nodes['count']=count
        
        if page==maxpage:
            list_nodes['previous']=None
            if page==1:
                list_nodes['next']=None
            else:
                list_nodes['next']=LIST_SNAPSHOTS_URL+"?page=%d" % (page-1)
        else:
            list_nodes['previous']=LIST_SNAPSHOTS_URL+"?page=%d" % (page+1)
            list_nodes['next']=LIST_SNAPSHOTS_URL+"?page=%d" % (page-1)
                    
        if page==1:
            list_nodes['next']=None
        
        """    
        result=[]
        for i in range(100):
            pos=i+(page-1)*100
            if pos<count:
                result.append(results[pos])
            else:
                break
        """    
                                                
        list_nodes['results']=results[(page-1)*page_per:page*page_per]
        
        return jsonify(list_nodes)

@app.route('/vpbitnodes/api/v1.0/snapshots/<timestamp>/', methods=['GET'])
def list_nodes_from_export(timestamp):
    bfind = False
    pos = 0
    parser = reqparse.RequestParser()
    parser.add_argument('field',help='field')
    try:
        args = parser.parse_args()   
        arg=args['field']
        if arg is not None:
            bfield,pos=util.get_field(arg)  
    except Exception,ex:
        pass
    
    list_time=None
    if(timestamp=="latest"):
        list_time=int(time.time())
    else:
        try:
            list_time=int(timestamp)
        except Exception,ex:
            list_time=int(timestamp)

    search_name,search_time,next_time,previous_time=util.search_file(EXPORT_PATH,list_time)

    if search_name is None:
        return jsonify({'details': 'Not found'})
    else:
        f=open(search_name, 'r')
        datastore = json.load(f)
        f.close()
        list_nodes={}
        list_nodes["timestamp"]=int(search_time)
        
        if arg is None:        
            nodes={}
            height=0
            node_nums=0
            for data in datastore:
                data_len=len(data)
                if data_len!=22:
                    continue;
                list1=[]
                
                key=data[0].encode('utf8')+":"+str(data[1])                
                for i in range(data_len-2):
                    list1.append(data[i+2])
                    if height<data[6]:
                        height=data[6]
                nodes[key]=list1
                node_nums=node_nums+1
            list_nodes['total_nodes']=node_nums
            list_nodes['latest_height']=height
            list_nodes['nodes']=nodes
        else:
            if bfield:
                nodes=[]
                height=0
                node_nums=0
                for data in datastore:
                    data_len=len(data)
                    if data_len!=22:
                        continue;
                    list1=[]
                    
                    for i in range(data_len-2):
                        if pos==8:
                            if (i==pos or i==pos+1):
                                list1.append(data[i+2])
                        elif pos<8:
                            if i==pos:
                                list1.append(data[i+2])                           
                        else:
                            if i==pos+1:
                                list1.append(data[i+2])                           
                            
                        if height<data[6]:
                            height=data[6]
                    nodes.append(list1)
                    node_nums=node_nums+1
                list_nodes['total_nodes']=node_nums
                list_nodes['latest_height']=height
                list_nodes[arg]=nodes
            else:
                return jsonify({'snapshots timestamp': 'no snapshot'})
            
        return jsonify(list_nodes)

@app.route('/vpbitnodes/api/v1.0/coldstakes/<timestamp>/', methods=['GET'])
@app.route('/vpbitnodes/api/v1.0/coldstakes/', methods=['GET'])
def get_cold_nodes_from_export(timestamp=None):
    page_per=10000
    bfind = False
    pos = 0
    
    parser = reqparse.RequestParser()
    parser.add_argument('q',help='q')
    parser.add_argument('page',help='page')
    try:
        args = parser.parse_args()   
    
        q=args['q']
        page=args['page']
        #print(q)
        #print(page)
    except Exception,ex:
        page=1
        pass    
    
    list_time=None
    if timestamp is None:
        list_time=int(time.time())
    else:
        if(timestamp=="latest"):
            list_time=int(time.time())
        else:
            try:
                list_time=int(timestamp)
            except Exception,ex:
                list_time=int(timestamp)
    
    search_name,search_time,next_time,previous_time=util.search_file(EXPORT_PATH,list_time)
    #print('test')
    #print(search_name,search_time,next_time,previous_time)
    coldstakes={}
    if search_name is None:
        return jsonify({'details': 'Not found'})
    else:                        
        f=open(search_name, 'r')
        datastore = json.load(f)
        f.close()
        list_nodes={}
        list_nodes["timestamp"]=int(search_time)
        
        for data in datastore:
            #print('111111')
            data_len=len(data)
            #print data_len
            if data_len!=22:
                continue;
            
            key=data[0].encode('utf8')+":"+str(data[1])                

	    coldlists = data[21]
            for coldstake in coldlists:
                coldaddress = coldstake["addresses"][0]
		stakevalue = coldstake["value"]
                #print coldaddress
		if coldaddress in coldstakes.keys():
		    coldstakes[coldaddress]["value"] += stakevalue 
		else:
		    tmpcoldstake={}
                    #print stakevalue
                    tmpcoldstake["value"] = stakevalue
                    #print tmpcoldstake["value"]
                    tmpcoldstake["onlineaddress"] = key
		    #print tmpcoldstake
		    #coldstakes[coldaddress]["value"] = 1 
                    #coldstakes[coldaddress]["onlineaddress"] = key 
                    coldstakes[coldaddress] = tmpcoldstake 

    return jsonify(coldstakes)

@app.route('/vpbitnodes/api/v1.0/nodes/<timestamp>/', methods=['GET'])
@app.route('/vpbitnodes/api/v1.0/nodes/', methods=['GET'])
def get_nodes_from_export(timestamp=None):
    page_per=10000
    bfind = False
    pos = 0
    
    parser = reqparse.RequestParser()
    parser.add_argument('q',help='q')
    parser.add_argument('page',help='page')
    try:
        args = parser.parse_args()   
    
        q=args['q']
        page=args['page']
        #print(q)
        #print(page)
    except Exception,ex:
        page=1
        pass    
    
    list_time=None
    if timestamp is None:
        list_time=int(time.time())
    else:
        if(timestamp=="latest"):
            list_time=int(time.time())
        else:
            try:
                list_time=int(timestamp)
            except Exception,ex:
                list_time=int(timestamp)
    
    search_name,search_time,next_time,previous_time=util.search_file(EXPORT_PATH,list_time)
    #print('test')
    #print(search_name,search_time,next_time,previous_time)
    if search_name is None:
        return jsonify({'details': 'Not found'})
    else:                        
        f=open(search_name, 'r')
        datastore = json.load(f)
        f.close()
        list_nodes={}
        list_nodes["timestamp"]=int(search_time)
        
        nodes={}
        height=0
        node_nums=0
        ipv4_nums=0
        ipv6_nums=0
        onion_nums=0
        agents={}
        countrys={}
        networks={}
        for data in datastore:
            #print('111111')
            data_len=len(data)
            #print data_len
            if data_len!=22:
                continue;
            list1=[]
            
            key=data[0].encode('utf8')+":"+str(data[1])                
            for i in range(data_len-2):
                list1.append(data[i+2])
                if height<data[6]:
                    height=data[6]

            location=get_location(list1[8], list1[9])
            list1.append(location["city"])
            list1.append(location["country"])
		
            if data[3] in agents.keys():
                agents[data[3]]+=1
            else:
                agents[data[3]]=1
                    
            if location["country"] in countrys.keys():
                countrys[location["country"]]+=1
            else:
                countrys[location["country"]]=1

            if data[14] in networks.keys():
                networks[data[14]]+=1
            else:
                networks[data[14]]=1
            
            #city=get_location(list1[8], list1[9])
            #list1.append(city)
    
            nodes[key]=list1
            node_nums=node_nums+1
            #print(key)            
                        
        if page is None:
            page=1
        else:
            page=int(page)
            
        if page==0:
            page=1
       
	#print('test666') 
        maxpage=(node_nums+page_per-1)/page_per
        #print node_nums
        #print page_per
        #print page
        if page>maxpage:
            return jsonify({'details': 'Not found'})
                                  
        list_nodes['latest_height']=height
        list_nodes['total_nodes']=node_nums
        
        sorted_key_list = sorted(agents, key=lambda x:agents[x], reverse=True)      
        sorted_dict = list(map(lambda x:{x:agents[x]}, sorted_key_list))                    
        list_nodes['agents']=sorted_dict        
        
        sorted_key_list = sorted(countrys, key=lambda x:countrys[x], reverse=True)      
        sorted_dict = list(map(lambda x:{x:countrys[x]}, sorted_key_list))                    
        list_nodes['countrys']=sorted_dict                
        
        sorted_key_list = sorted(networks, key=lambda x:networks[x], reverse=True)      
        sorted_dict = list(map(lambda x:{x:networks[x]}, sorted_key_list))                    
        list_nodes['networks']=sorted_dict                    
        
        if q is None:        
            search_nodes_nums=node_nums        
            list_nodes['nodes']=util.dict_slice(nodes, (page-1)*page_per, page*page_per)
        else:
            nodess,search_nodes_nums=util.find_nodes_by_field(nodes,q)        
            list_nodes['nodes']=util.dict_slice(nodess, (page-1)*page_per, page*page_per)

        list_nodes['search_nodes']=search_nodes_nums
        list_nodes['next']=next_time
        list_nodes['previous']=previous_time
        
        return jsonify(list_nodes) 

@app.route('/vpbitnodes/api/v1.0/getnodesinfobyip/<timestamp>/', methods=['GET'])
@app.route('/vpbitnodes/api/v1.0/getnodesinfobyip/', methods=['GET'])
def get_nodesinfo_by_ip_from_export(timestamp=None):
    bfind = False
    pos = 0
    
    parser = reqparse.RequestParser()
    parser.add_argument('q',help='q')
    parser.add_argument('ip',help='ip')
    try:
        args = parser.parse_args()   
    
        q=args['q']
        ip=args['ip']
        #print(q)
        #print(page)
    except Exception,ex:
        return jsonify({})    
    
    list_time=None
    if timestamp is None:
        list_time=int(time.time())
    else:
        if(timestamp=="latest"):
            list_time=int(time.time())
        else:
            try:
                list_time=int(timestamp)
            except Exception,ex:
                list_time=int(timestamp)
    
    search_name,search_time,next_time,previous_time=util.search_file(EXPORT_PATH,list_time)
    #print('test')
    #print(search_name,search_time,next_time,previous_time)
    if search_name is None:
        return jsonify({})
    else:                        
        f=open(search_name, 'r')
        datastore = json.load(f)
        f.close()
        list_nodes={}
        list_nodes["timestamp"]=int(search_time)
        
        nodes={}
        height=0
        node_nums=0
        ipv4_nums=0
        ipv6_nums=0
        onion_nums=0
        agents={}
        countrys={}
        networks={}
        for data in datastore:
            #print('111111')
            data_len=len(data)
            #print data_len
            if data_len!=22:
                continue;
            if data[0] != ip:
                continue
            list1={}
            #list1={'address':'','protocol':0,'version':0,'height':0, 'city':'','country':'','network':''}
            #print data

            key=data[0].encode('utf8')+":"+str(data[1])
            list1['address'] = key
            list1['height'] = 0                
            for i in range(data_len-2):
                #list1.address = data[i+2]
                #list1.append(data[i+2])
                if list1['height']<data[6]:
                    list1['height']=data[6]

            location=get_location(data[10], data[11])
            list1['city'] = location["city"]
            list1['country'] = location["country"]
            list1['protocol'] = data[2]
            list1['version'] = data[3]
            list1['network'] = data[14]
            list1['asns'] = data[13]
    
            return jsonify(list1)

@app.route('/vpbitnodes/api/v1.0/nodesinfo/<timestamp>/', methods=['GET'])
@app.route('/vpbitnodes/api/v1.0/nodesinfo/', methods=['GET'])
def get_nodesinfo_from_export(timestamp=None):
    page_per=10
    bfind = False
    pos = 0
    
    parser = reqparse.RequestParser()
    parser.add_argument('q',help='q')
    parser.add_argument('page',help='page')
    try:
        args = parser.parse_args()   
    
        q=args['q']
        page=args['page']
        #print(q)
        #print(page)
    except Exception,ex:
        page=1
        pass    
    
    list_time=None
    if timestamp is None:
        list_time=int(time.time())
    else:
        if(timestamp=="latest"):
            list_time=int(time.time())
        else:
            try:
                list_time=int(timestamp)
            except Exception,ex:
                list_time=int(timestamp)
    
    search_name,search_time,next_time,previous_time=util.search_file(EXPORT_PATH,list_time)
    #print('test')
    #print(search_name,search_time,next_time,previous_time)
    if search_name is None:
        return jsonify({})
    else:                        
        f=open(search_name, 'r')
        datastore = json.load(f)
        f.close()
        list_nodes={}
        list_nodes["timestamp"]=int(search_time)
        
        nodes={}
        height=0
        node_nums=0
        ipv4_nums=0
        ipv6_nums=0
        onion_nums=0
        agents={}
        countrys={}
        networks={}
        for data in datastore:
            #print('111111')
            data_len=len(data)
            #print data_len
            if data_len!=22:
                continue;
            list1={}
            #list1={'address':'','protocol':0,'version':0,'height':0, 'city':'','country':'','network':''}
            print data
            key=data[0].encode('utf8')+":"+str(data[1])
            list1['address'] = key
            list1['height'] = 0                
            for i in range(data_len-2):
                #list1.address = data[i+2]
                #list1.append(data[i+2])
                if list1['height']<data[6]:
                    list1['height']=data[6]

            location=get_location(data[10], data[11])
            list1['city'] = location["city"]
            list1['country'] = location["country"]
            list1['protocol'] = data[2]
            list1['version'] = data[3]
            list1['network'] = data[14]
            list1['asns'] = data[13]
    
            nodes[key] = list1
            node_nums=node_nums+1
            #print(key)            
                        
        if page is None:
            page=1
        else:
            page=int(page)
            
        if page==0:
            page=1
       
	#print('test666') 
        maxpage=(node_nums+page_per-1)/page_per
        #print node_nums
        #print page_per
        #print page
        if page>maxpage:
            return jsonify({})                   
        
        if q is None:        
            search_nodes_nums=node_nums        
            list_nodes['nodes']=util.dict_slice(nodes, (page-1)*page_per, page*page_per)
        else:
            nodess,search_nodes_nums=util.find_nodes_by_field(nodes,q)        
            list_nodes['nodes']=util.dict_slice(nodess, (page-1)*page_per, page*page_per)
        
        return jsonify(list_nodes['nodes'])


@app.route('/vpbitnodes/api/v1.0/nodesnum/<timestamp>/', methods=['GET'])
@app.route('/vpbitnodes/api/v1.0/nodesnum/', methods=['GET'])
def get_nodesnum_from_export(timestamp=None):
    list_time=None
    if timestamp is None:
        list_time=int(time.time())
    else:
        if(timestamp=="latest"):
            list_time=int(time.time())
        else:
            try:
                list_time=int(timestamp)
            except Exception,ex:
                list_time=int(timestamp)
    
    search_name,search_time,next_time,previous_time=util.search_file(EXPORT_PATH,list_time)
    #print('test')
    #print(search_name,search_time,next_time,previous_time)
    if search_name is None:
        return jsonify({'num': 0})
    else:                        
        f=open(search_name, 'r')
        datastore = json.load(f)
        f.close()
        return jsonify({'num': len(datastore)})    

@app.route('/vpbitnodes/api/v1.0/nodes/<address>-<port>', methods=['GET'])
def node_status(address,port):    
    results={}
    nodes=util.search_node_from_address(address,port)    
    results['hostname']=""
    results['address']=address
    if util.find_node_from_redis(REDIS_CONN,address,port):
        results['status']="UP"
    else:
        results['status']="DOWN"
    results['data']=nodes
    results['bitcoin_address']=""    
    results['url']=""
    results['verified']="false"
    results['mbps']=0
    return jsonify(results)

@app.route('/vpbitnodes/api/v1.0/nodes/<address>-<port>/latency', methods=['GET'])
def node_status_latency(address,port):    
    results={}
    nodes=util.search_node_from_address(address,port)    
    
    results['hostname']=""
    results['address']=address
    results['status']="UP"
    results['data']=nodes
    results['bitcoin_address']=""    
    results['url']=""
    results['verified']="false"
    results['mbps']=3.452
    return jsonify(results)

@app.route('/vpbitnodes/api/v1.0/inv/<inv_hash>/', methods=['GET'])
def get_data_propagation(inv_hash):   
    #print(inv_hash)
    invs_hash=util.get_inv_hash_from_redis(REDIS_CONN,inv_hash)    
    if invs_hash is None:
        return jsonify({'detail': 'Not found'})
    
    nodes_hash=util.get_nodes_hash_from_redis(REDIS_CONN)
    if nodes_hash is None:
        return jsonify({'detail': 'Not found'})
    
    results={}
    stats={}
    heads=[]
    min=0
    max=0
    mean=0
    std=0
    a50=0
    a90=0 
    results['inv_hash']=inv_hash
    lens=len(invs_hash)
    totals=0
    deltas=[]
    
    if lens>0:
        max=int(invs_hash[0][1])
        min=int(invs_hash[lens-1][1])
        
    i=0
    for i in range(lens):
        node=nodes_hash[invs_hash[lens-1-i][0]]        
        if  node is not None:
            totals+=1
            if totals<=10:
                nodes=[]
                nodes.append(node)
                nodes.append(int(invs_hash[lens-1-i][1]))
                heads.append(nodes)
            deltas.append(int(invs_hash[lens-1-i][1])-min)
            
    stats['head']=heads
    stats['min']=numpy.min(deltas)
    stats['max']=numpy.max(deltas)
    stats['mean']=int(numpy.mean(deltas))
    stats['std']=int(numpy.std(deltas,ddof=1))
    stats['50%']=int(numpy.percentile(deltas, 50))
    stats['90%']=int(numpy.percentile(deltas,90))
    results['stats']=stats
    
    return jsonify(results)

@app.route('/vpbitnodes/api/v1.0/vpubboard/<days>/', methods=['GET'])
def list_board_nodes_from_export(days):   
    results={}
    agents_time={}
    agents={}
    countrys_time={}    
    countrys={}
    asns_time={}
    asns={}
    network_time={}
    network={}
    nodes_time=[]
    total={}
    total_time={}
    
    list_time=None
    list_time=int(time.time()) - int(days) * 86400
    #print('list_time')
    #print(list_time)
    #list_time=int(time.time())

    json_list=sorted(os.listdir(EXPORT_PATH), reverse=True)
    json_nums=len(json_list)
    print("json_nums=")
    print(json_nums)
    if json_nums==0:
        return jsonify(results)
    
    json_name=EXPORT_PATH+'/'+json_list[0]
    if os.path.isfile(json_name):
        file_times,ext=json_list[0].split(".")
        file_time=int(file_times)
        a=time.localtime(file_time)
        minu=a.tm_min
        #pos=(minu+5)/6
        b=time.strftime("%Y-%m-%d %H:00:00", a)
        b=time.mktime(time.strptime(b,'%Y-%m-%d %H:%M:%S')) 
    else:
        return jsonify(results)
        
    xaias=[]
    n=0
    nums=0
    for i in range(json_nums):
        #print("i=")
        #print(i)
        json_name=EXPORT_PATH+'/'+json_list[i]
        if os.path.isfile(json_name):
            #print json_list[i]
            file_times,ext=json_list[i].split(".")
            try:
                file_time=int(file_times)
		if file_time < list_time:
                    #print "file_name="
                    #print(json_name)
		    continue
            except Exception,ex:
                continue            
            a=time.localtime(file_time)
            
            if n==0 :
                    
                xaias.append(b)
                #print(json_name) 
                f=open(json_name, 'r')
                datastore = json.load(f)
                f.close()
                #print "load file_name="
                #print(json_name)

                total=0
                for data in datastore:
                    data_len=len(data)
                    if data_len!=22:
	                #print "file_name="
                        #print(json_name)
                        continue;
                    total+=1
                    list1=[]
                    key=""
                    key=data[0].encode('utf8')+":"+str(data[1])
                    for i in range(data_len-2):
                        list1.append(data[i+2])
                    
                    location=get_location(list1[8], list1[9])
                    list1.append(location)

                    if list1[1] in agents.keys():
                        agents[list1[1]]+=1
                    else:
                        agents[list1[1]]=1 
                    
                    if location["country"] is None:
                        if location["country"] in countrys.keys():
                            countrys['other']+=1
                        else:
                            countrys['other']=1 
                    else:
                        if location["country"] in countrys.keys():
                            countrys[location["country"]]+=1
                        else:
                            countrys[location["country"]]=1 
                                        
                    if list1[11] is None:
                        if list1[11] in asns.keys():
                            asns['other']+=1
                        else:
                            asns['other']=1 
                    else:
                        if list1[11] in asns.keys():
                            asns[list1[11]]+=1
                        else:
                            asns[list1[11]]=1

                    if list1[12] is None:
                        if list1[12] in network.keys():
                            network['other']+=1
                        else:
                            network['other']=1 
                    else:
                        if list1[12] in network.keys():
                            network[list1[12]]+=1
                        else:
                            network[list1[12]]=1 

                sorted_key_list = sorted(agents, key=lambda x:agents[x], reverse=True)      
                sorted_dict = list(map(lambda x:{x:agents[x]}, sorted_key_list))                    
		agents_time[file_time] = sorted_dict
		#agents_time.append(sorted_dict)
                agents={}
                
                sorted_key_list = sorted(countrys, key=lambda x:countrys[x], reverse=True)      
                sorted_dict = list(map(lambda x:{x:countrys[x]}, sorted_key_list))                    
                countrys_time[file_time] = sorted_dict
		#countrys_time.append(sorted_dict)
                countrys={}
                
                sorted_key_list = sorted(asns, key=lambda x:asns[x], reverse=True)      
                sorted_dict = list(map(lambda x:{x:asns[x]}, sorted_key_list))                    
                asns_time[file_time] = sorted_dict
		#asns_time.append(sorted_dict)
                asns={}

                sorted_key_list = sorted(network, key=lambda x:network[x], reverse=True)      
                sorted_dict = list(map(lambda x:{x:network[x]}, sorted_key_list))                    
                network_time[file_time] = sorted_dict
		#network_time.append(sorted_dict)
                network={}
                
                total_time[file_time] = total
                #total_time.append(total)
		nodes_time.append(total)
                nums+=1
                #if nums>=48:
                #    break
                n=1
            else:
                n-=1
                continue
    
    results['times']=int(b)
    results['agents']=agents_time       
    results['countrys']=countrys_time   
    results['asns']=asns_time   
    results['nodes']=nodes_time
    results['network']=network_time
    results['total']=total_time
                
    return jsonify(results)

@app.route('/vpbitnodes/api/v1.0/dashboard/', methods=['GET'])
def list_24h_nodes_from_export():   
    results={}
    agents_time=[]
    agents={}
    countrys_time=[]    
    countrys={}
    asns_time=[]    
    asns={}
    nodes_time=[]
    
    list_time=None
    list_time=int(time.time()) 

    json_list=sorted(os.listdir(EXPORT_PATH), reverse=True)
    json_nums=len(json_list)
    if json_nums==0:
        return jsonify(results)
    
    json_name=EXPORT_PATH+'/'+json_list[0]
    if os.path.isfile(json_name):
        file_times,ext=json_list[0].split(".")
        file_time=int(file_times)
        a=time.localtime(file_time)
        minu=a.tm_min
        #pos=(minu+5)/6
        b=time.strftime("%Y-%m-%d %H:00:00", a)
        b=time.mktime(time.strptime(b,'%Y-%m-%d %H:%M:%S')) 
    else:
        return jsonify(results)
        
    xaias=[]
    n=0
    nums=0
    for i in range(json_nums):
        json_name=EXPORT_PATH+'/'+json_list[i]
        if os.path.isfile(json_name):
            file_times,ext=json_list[i].split(".")
            try:
                file_time=int(file_times)
            except Exception,ex:
                continue            
            a=time.localtime(file_time)
            if n==0 :
                    
                xaias.append(b)
                
                f=open(json_name, 'r')
                datastore = json.load(f)
                f.close()
                
                total=0
                for data in datastore:
                    data_len=len(data)
                    if data_len!=22:
                        continue;
                    total+=1
                    list1=[]
                    key=""
                    key=data[0].encode('utf8')+":"+str(data[1])
                    for i in range(data_len-2):
                        list1.append(data[i+2])
                        
                    if list1[1] in agents.keys():
                        agents[list1[1]]+=1
                    else:
                        agents[list1[1]]=1 
                    
                    if list1[7] is None:
                        if list1[7] in countrys.keys():
                            countrys['other']+=1
                        else:
                            countrys['other']=1 
                    else:
                        if list1[7] in countrys.keys():
                            countrys[list1[7]]+=1
                        else:
                            countrys[list1[7]]=1 
                                        
                        if list1[11] is None:
                            if list1[11] in asns.keys():
                                asns['other']+=1
                            else:
                                asns['other']=1 
                        else:
                            if list1[11] in asns.keys():
                                asns[list1[11]]+=1
                            else:
                                asns[list1[11]]=1 

                sorted_key_list = sorted(agents, key=lambda x:agents[x], reverse=True)      
                sorted_dict = list(map(lambda x:{x:agents[x]}, sorted_key_list))                    
                agents_time.append(sorted_dict)
                agents={}
                
                sorted_key_list = sorted(countrys, key=lambda x:countrys[x], reverse=True)      
                sorted_dict = list(map(lambda x:{x:countrys[x]}, sorted_key_list))                    
                countrys_time.append(sorted_dict)
                countrys={}
                
                sorted_key_list = sorted(asns, key=lambda x:asns[x], reverse=True)      
                sorted_dict = list(map(lambda x:{x:asns[x]}, sorted_key_list))                    
                asns_time.append(sorted_dict)
                asns={}
                
                nodes_time.append(total)
                nums+=1
                if nums>=48:
                    break
                n=5
            else:
                n-=1
                continue
    
    results['times']=int(b)
    results['agents']=agents_time       
    results['countrys']=countrys_time   
    results['asns']=asns_time   
    results['nodes']=nodes_time
                
    return jsonify(results)

def init_conf(argv):
    """
    Populates CONF with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    CONF['logfile'] = conf.get('ping', 'logfile')
    CONF['magic_number'] = unhexlify(conf.get('ping', 'magic_number'))
    CONF['db'] = conf.getint('ping', 'db')
    CONF['debug'] = conf.getboolean('ping', 'debug')
    CONF['ttl'] = conf.getint('ping', 'ttl')
    CONF['crawl_dir'] = conf.get('ping', 'crawl_dir')

    # Set to True for master process
    #CONF['master'] = argv[2] == "master"

if  __name__ == '__main__':
    # Initialize global conf
  
    pp=[]
    global REDIS_CONN
    REDIS_CONN = new_redis_conn(0)#db=CONF['db'])
    if REDIS_CONN == None:
        print 'redis is nil'
    

    height = REDIS_CONN.get('height')
    
    #b1=[]
    #b2=[]
    
    #for key in get_keys(REDIS_CONN, 'ping:*'):
    #    aa=REDIS_CONN.lrange(key,0,-1)
    #    b1.append(int(aa[0]))
        #b2.append(int(aa[1]))
    #bb1=sorted(b1,reverse=True)
    #bb2=b2.sorted()
    
    #for kk in bb1:
    #    timeStamp=int(kk)/1000
    #    timeArray = time.localtime(timeStamp)
    #    otherStyleTime = time.strftime("%Y--%m--%d %H:%M:%S", timeArray)
    #    print otherStyleTime   # 2013--10--10 23:40:00        
        
    #list_nodes_from_export(1550903402)
    
    #get_nodes_from_export('1548813810')
    #list_24h_nodes_from_export()
    #opens = REDIS_CONN.scard('open')
    #open=REDIS_CONN.smembers('open')
    
    #get_data_propagation('0000000f90117ec9d3ef9513a42c9ff25ebc4a15a519f89eaa6cc7b2b9d87775')
    
    #hashs=util.get_inv_hash_from_redis(REDIS_CONN,'00000000c18b05f28160fc9e7757dba669f9879208249bbaf908ae0c48c25333')
    #nodes_hash=util.get_nodes_hash_from_redis(REDIS_CONN)
    #for hash in hashs:
    #    print(hash)
    #    print(type(hash))
    #    bb=nodes_hash[hash[0]]
    #    if  bb is not None:
    #        print("kk")
    
    #open1=REDIS_CONN.zcard('inv:2:00000026517ca6a157485dc9125c696f0d7655be60b7bb834483674fd4daec17')#,1550020691514)
    #open2=REDIS_CONN.zrevrange('inv:2:00000026517ca6a157485dc9125c696f0d7655be60b7bb834483674fd4daec17',0,-1)#,1550020691514)

    #nodes = REDIS_CONN.lrange('rtt:118.190.201.80-9900',0,-1)
    #nodd=util.get_node_rtt_from_redis(REDIS_CONN,'118.190.201.80-9900')
    
    #nodes = REDIS_CONN.zrange('inv:2:000000059eaccaefe53056e013bea89984940a52a2efc01879b0d451ecf12a88',0,-1,withscores=True)
    #for node in nodes:
    #    print(node)
    
    CORS(app, supports_credentials=True)
    
    app.run( host = '0.0.0.0',
        port = 5000,  debug=True)
