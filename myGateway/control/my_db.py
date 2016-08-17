#coding=utf-8
import json
from modules.database import *
from util import SERVER_IP, send_req
from ryu.lib import dpid as dpid_lib

URL_REST_DB = {
    'flow':'/stats/flow/{dpid}',
    'gateway':'/table_gateway',
    'dpid_all':'/table_dpid', 
    'dpid':'/table_dpid/{dpid}', 
    'dpid_list':'/table_dpid_list', 
    'device':'/table_device',
    'mac':'/table_mac/{ip_addr}'
}  

def get_gateway():
    gws = json.loads(send_req(SERVER_IP+URL_REST_DB['gateway']))
    if None == gws:
        return None

    for gw in gws:
        gw['dpid'] = gw['more']['dpid']
        gw['port'] = gw['more']['port']
    return gws

def get_dpid_all():
    db = database('modules/USERDATA.db')
    dpall = json.loads(send_req(SERVER_IP+URL_REST_DB['dpid_all']))
    if None == dpall:
        return None

    for dev in dpall:
        rcd_user = db.findUSERByX('USER_ID',dev['user'])
        for user in rcd_user:
            dev['more'] = {}
            dev['more']['depart'] = user[2].encode('utf-8')
            dev['more']['position'] = user[3].encode('utf-8')
            dev['more']['name'] = user[4].encode('utf-8')
    return dpall

def get_dpid(dpid):
    dpid = dpid_lib.dpid_to_str(dpid)
    db = database('modules/USERDATA.db')
    table_dpid = json.loads(send_req(SERVER_IP+URL_REST_DB['dpid'].format(dpid=dpid)))
    if None == table_dpid:
        return None

    for dev in table_dpid:
        rcd_user = db.findUSERByX('USER_ID',dev['user'])
        for user in rcd_user:
            dev['more'] = {}
            dev['more']['depart'] = user[2].encode('utf-8')
            dev['more']['position'] = user[3].encode('utf-8')
            dev['more']['name'] = user[4].encode('utf-8')
    return table_dpid

def get_dpid_list():
    return json.loads(send_req(SERVER_IP+URL_REST_DB['dpid_list']))

def get_device():
    db = database('modules/USERDATA.db')
    devs = json.loads(send_req(SERVER_IP+URL_REST_DB['device']))
    if None == devs:
        return None

    for dev in devs:
        rcd_user = db.findUSERByX('USER_ID',dev['user'])[0]
        dev['ip'] = dev['more']['ip'].encode('utf-8')
        dev['dpid'] = dev['more']['dpid']
        dev['port'] = dev['more']['port']
        dev['more']['depart'] = rcd_user[2].encode('utf-8')
        dev['more']['position'] = rcd_user[3].encode('utf-8')
        dev['more']['name'] = rcd_user[4].encode('utf-8')
    return devs

def get_user(ip_addr):
    devs = get_device()
    if None == devs:
        return None
    else:
        for dev in devs:
            if ip_addr == dev['ip']:
                return dev['user'], dev['more']['name']
        return None

def get_table(order,dpid=None):
    data = {}
    data['dpid_list'] = get_dpid_list()
    if 'dev' == order:
        data['dev'] = get_device()
    elif 'gw' == order:
        data['gw'] = get_gateway()
    elif 'dpall' == order:
        data['dpall'] = get_dpid_all()
    elif 'dp' == order:
        data['dp'] = get_dpid(dpid)
    elif 'all' == order:
        data['dev'] = get_device()
        data['gw'] = get_gateway()
        data['dpall'] = get_dpid_all()
    else:
        print 'order error!'

    for x in data:
        if None == data[x]:
            print 'Connect to controller error!'
            return 0
    info = []            
    info.append(dict(data))
    return json.dumps(info)


def get_mac(ip_addr):
    return json.loads(send_req(SERVER_IP+URL_REST_DB['mac'].format(ip_addr=ip_addr)))

def get_flow(dpid):
    info = json.loads(send_req(SERVER_IP+URL_REST_DB['flow'].format(dpid=dpid)))
    if None == info:
        return None

    tmp = {'DPID':0,'PRIORITY':0,'TABLE_ID':0,'DTIME':0,'ITIME':0,'HTIME':0,'MATCH':'a','ACTIONS':'a'}
    tmp['DPID'] = dpid
    table = []
    for flow in info[str(dpid)]:
        tmp['PRIORITY'] = flow['priority']
        tmp['TABLE_ID'] = flow['table_id']
        tmp['DTIME'] = flow['duration_sec']
        tmp['ITIME'] = flow['idle_timeout']
        tmp['HTIME'] = flow['hard_timeout']
        tmp['MATCH'] = json.dumps(flow['match'])
        tmp['ACTIONS'] = json.dumps(flow['actions'])
        table.append(dict(tmp))
    return table

def get_flow_all(dplist):
    data = []
    for dpid in dplist:
        data = data + get_flow(dpid=dpid)
    return data

def get_flow_table(x,dpid=None):
    data = {}
    data['dpid_list'] = get_dpid_list()
    if 'dp' == x:
        data['dp'] = get_flow(dpid)
    else:
        data['dpall'] = get_flow_all(data['dpid_list'])

    for x in data:
        if None in data[x]:
            print 'Connect to controller error!'
            return 0
    info = []            
    info.append(dict(data))
    return json.dumps(info)

