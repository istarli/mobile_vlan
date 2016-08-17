#coding=utf-8
import json
from modules.database import *
from util import SERVER_IP, send_req
from ryu.lib import dpid as dpid_lib

URL_REST_TOPO = {
	'switches':'/v1.0/topology/switches',
	'links_all':'/v1.0/topology/links',	
	'hosts_all':'/v1.0/topology/hosts'
}

def u2s(a):
	return a.encode('utf-8')

def get_switches():
	return json.loads(send_req(SERVER_IP+URL_REST_TOPO['switches']))

def get_links():
	return json.loads(send_req(SERVER_IP+URL_REST_TOPO['links_all']))

def get_hosts():
	return json.loads(send_req(SERVER_IP+URL_REST_TOPO['hosts_all']))

def analyze_switch(switches):
	nodes_swt = []
	i = 1
	for swt in switches:
		tmp = {'name':dpid_lib.str_to_dpid(swt['dpid']),'flag':0 }
		i = i + 1
		nodes_swt.append(dict(tmp))
	return nodes_swt

def analyze_host(hosts):
	db = database('modules/USERDATA.db')
	nodes_host = []
	i = 0
	for host in hosts:
		flag = 1
		if host['user_id'] != 0:
			rcd = db.findUSERByX('USER_ID',host['user_id'])[0]
			depart, position, name = u2s(rcd[2]), u2s(rcd[3]), u2s(rcd[4])
		else:
			depart, position, name = 'SDN_FiLL', 'Admin', 'Gateway'
			flag = 2
		tmp = { 'name':host['user_id'],
				'flag':flag, 
				'more':{
					'mac':u2s(host['mac']),
					'ip':u2s(host['ip']),
					'vlan':host['vlan'],
					'name':name,
					'depart':depart,
					'position':position
				}
			}
		i = i + 1
		nodes_host.append(dict(tmp))

	return nodes_host

def analyze_node(switches,hosts):
	nodes_swt = analyze_switch(switches)
	nodes_host = analyze_host(hosts)
	nodes = nodes_swt + nodes_host
	return nodes

def analyze_link(links,switches,hosts):
	edges = []
	item = {}
	i = 0
	nodes_id = {}
	for swt in switches:
		tmp = swt['dpid']
		nodes_id[tmp] = i
		i = i + 1
	num_swt = i

	for host in hosts:
		dpid_str = host['dpid'].encode('utf-8')
		item = {'source':i,'target':nodes_id[dpid_str],'ps':0,'pt':host['port']}
		edges.append(dict(item))
		i = i + 1

	num_link = len(links)/2
	i = 0
	while i < num_link:
		dpid_src = links[i]['src']['dpid']
		dpid_dst = links[i]['dst']['dpid']
		item = {'source':nodes_id[dpid_src],
				'target':nodes_id[dpid_dst], 
				'ps':int(links[i]['src']['port_no']), 
				'pt':int(links[i]['dst']['port_no'])
		}
		edges.append(dict(item))
		i = i + 1

	return edges

def analyze_topo():
	switches = get_switches()
	hosts = get_hosts()
	links = get_links()
	if None in [switches, hosts, links]:
		print 'Connect to controller error!'
		return 0, 0
	else:
		nodes = analyze_node(switches,hosts)
		edges = analyze_link(links,switches,hosts)
		return json.dumps(nodes),json.dumps(edges)
