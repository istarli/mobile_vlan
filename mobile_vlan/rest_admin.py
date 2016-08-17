# Copyright (C) 2013 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from webob import Response

from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.base import app_manager
from ryu.lib import dpid as dpid_lib
from ryu.topology.api import get_switch, get_link, get_host

from database.database import *

# REST API for switch configuration
#
# get all the switches
# GET /v1.0/topology/switches
#
# get the switch
# GET /v1.0/topology/switches/<dpid>
#
# get all the links
# GET /v1.0/topology/links
#
# get the links of a switch
# GET /v1.0/topology/links/<dpid>
#
# get all the hosts
# GET /v1.0/topology/hosts
#
# get the hosts of a switch
# GET /v1.0/topology/hosts/<dpid>
#
# where
# <dpid>: datapath id in 16 hex
DB_PATH = './ryu/app/mobile_vlan/database/CONTROLLER_DATA.db'

class TopologyAPI(app_manager.RyuApp):
    _CONTEXTS = {
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(TopologyAPI, self).__init__(*args, **kwargs)

        wsgi = kwargs['wsgi']
        wsgi.register(TopologyController, {'topology_api_app': self})


class TopologyController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(TopologyController, self).__init__(req, link, data, **config)
        self.topology_api_app = data['topology_api_app']

    @route('topology', '/v1.0/topology/switches',
           methods=['GET'])
    def list_switches(self, req, **kwargs):
        return self._switches(req, **kwargs)

    @route('topology', '/v1.0/topology/switches/{dpid}',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_switch(self, req, **kwargs):
        return self._switches(req, **kwargs)

    @route('topology', '/v1.0/topology/links',
           methods=['GET'])
    def list_links(self, req, **kwargs):
        return self._links(req, **kwargs)

    @route('topology', '/v1.0/topology/links/{dpid}',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_links(self, req, **kwargs):
        return self._links(req, **kwargs)

    @route('topology', '/v1.0/topology/hosts',
           methods=['GET'])
    def list_hosts(self, req, **kwargs):
        return self._hosts(req, **kwargs)

    @route('topology', '/v1.0/topology/hosts/{dpid}',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_hosts(self, req, **kwargs):
        return self._hosts(req, **kwargs)


    @route('topology', '/table_gateway',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_gateway(self, req, **kwargs):
        return self._gateway(req, **kwargs)

    @route('topology', '/table_dpid',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_dpid_all(self, req, **kwargs):
        return self._dpid(req, **kwargs)

    @route('topology', '/table_dpid/{dpid}',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_dpid(self, req, **kwargs):
        return self._dpid(req, **kwargs)

    @route('topology', '/table_device',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_device(self, req, **kwargs):
        return self._device(req, **kwargs)

    @route('topology', '/table_dpid_list',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_dpid_list(self, req, **kwargs):
        return self._dpid_list(req, **kwargs)

    @route('topology', '/table_mac/{ip_addr}',methods=['GET'])
    def get_mac(self, req, **kwargs):
        return self._mac(req, **kwargs)

    def _switches(self, req, **kwargs):
        dpid = None
        if 'dpid' in kwargs:
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        switches = get_switch(self.topology_api_app, dpid)
        body = json.dumps([switch.to_dict() for switch in switches])
        return Response(content_type='application/json', body=body)

    def _links(self, req, **kwargs):
        dpid = None
        if 'dpid' in kwargs:
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        links = get_link(self.topology_api_app, dpid)
        body = json.dumps([link.to_dict() for link in links])
        return Response(content_type='application/json', body=body)

    def _hosts(self, req, **kwargs):
        body = None
        db = database(DB_PATH)

        if 'dpid' in kwargs:
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
            rcd_dpid = selectDPID(dpid=dpid)
            host_of_dpid = []
            tmp = {'mac':'a', 'port':0,'ip':'a', 'slave':1}
            for x in rcd_dpid:
                tmp['mac'], tmp['port'], tmp['ip'], tmp['slave'] = x[0].encode('utf-8'), x[1], x[2].encode('utf-8'), x[3]
                hosts_of_dpid.append(dict(tmp))
            body = json.dumps(hosts_of_dpid)
        else:
            rcd_dev = db.selectDEVICE()    
            hosts = []
            tmp = {'user_id':0, 'dpid':0,'mac':'a', 'vlan':0, 'ip': 'a', 'port':0}
            #add gateway
            tmp['mac'] = db.selectGATEWAY()[0][0].encode('utf-8')
            tmp['ip'] = db.selectGATEWAY()[0][1].encode('utf-8')
            gw_dpid = db.getDPIDBySlave(mac_addr=tmp['mac'])
            if None != gw_dpid:
                tmp['port'] = db.findDPIDByX(gw_dpid,'MAC_ADDR',tmp['mac'])[0][0]
                tmp['dpid'] = dpid_lib.dpid_to_str(gw_dpid)
                hosts.append(dict(tmp))
            #add host
            for dev in rcd_dev:
                tmp['mac'], tmp['vlan'], tmp['user_id'] = dev[0].encode('utf-8'), dev[1], dev[2]
                dpid = db.getDPIDBySlave(mac_addr=tmp['mac'])
                tmp['dpid'] = dpid_lib.dpid_to_str(dpid)
                rcd_host = db.findDPIDByX(dpid,'MAC_ADDR',tmp['mac'])
                tmp['port'], tmp['ip'] = rcd_host[0][0], rcd_host[0][1].encode('utf-8')
                hosts.append(dict(tmp))
            body = json.dumps(hosts)
        return Response(content_type='application/json', body=body)

    def _gateway(self, req, **kwargs):
        db = database(DB_PATH)
        rcd_gw = db.selectGATEWAY()
        gateway = []
        tmp = {'mac':'a','ip':'b','more':{}}
        for gw in rcd_gw:
            tmp['mac'], tmp['ip'] = gw[0].encode('utf-8'), gw[1].encode('utf-8')
            dpid = db.getDPIDBySlave(mac_addr=tmp['mac'])
            tmp['more']['dpid'] = dpid
            if dpid != None:
                rcd_dpid = db.findDPIDByX(dpid,'MAC_ADDR',tmp['mac'])
                tmp['more']['port'] = rcd_dpid[0][0]
            else:
                tmp['more']['port'] = None
            gateway.append(dict(tmp))
        body = json.dumps(gateway)
        return Response(content_type='application/json',body=body)

    def _dpid(self, req, **kwargs):
        body = None
        db = database(DB_PATH)

        if 'dpid' in kwargs:
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
            rcd_dpid = db.selectDPID(dpid=dpid)
            table_dpid = []
            tmp = {'mac':'a','port':0,'ip':'b','slave':0,'user':0}
            for x in rcd_dpid:
                tmp['mac'], tmp['port'], tmp['ip'], tmp['slave'] = x[0].encode('utf-8'), x[1], x[2].encode('utf-8'), x[3]
                rcd_device = db.findDEVICEByX('MAC_ADDR',tmp['mac'])
                if 0 == len(rcd_device):
                    tmp['user'] = 0;
                else:
                    tmp['user'] = rcd_device[0][1]
                table_dpid.append(dict(tmp))
            body = json.dumps(table_dpid)
        else:
            dpid_list = db.getDPIDLIST()
            rcd_dpid_all = db.selectMulDPID(dpid_list)
            dpid_all = []
            tmp = {'dplist':dpid_list,'dpid':1,'mac':'a','port':1,'ip':'b','slave':0,'user':0}
            for name in rcd_dpid_all:
                tmp['dpid'] = int(name[4:])
                for rcd in rcd_dpid_all[name]:
                    tmp['mac'], tmp['port'] = rcd[0].encode('utf-8'), rcd[1]
                    tmp['ip'], tmp['slave'] = rcd[2].encode('utf-8'), rcd[3]
                    rcd_device = db.findDEVICEByX('MAC_ADDR',tmp['mac'])
                    for dev in rcd_device:
                        tmp['user'] = dev[1]
                    dpid_all.append(dict(tmp))

            print dpid_all
            body = json.dumps(dpid_all)

        return Response(content_type='application/json', body=body)

    def _device(self, req, **kwargs):
        db = database(DB_PATH)
        rcd_dev = db.selectDEVICE()
        devs = []
        tmp = {'mac':'a', 'vlan':1, 'user':1}
        tmp2 = {'port':0,'dpid':0,'ip':'a'}
        for dev in rcd_dev:
            tmp['mac'], tmp['vlan'], tmp['user'] = dev[0].encode('utf-8'), dev[1], dev[2]
            dpid = db.getDPIDBySlave(mac_addr=tmp['mac'])
            tmp2['dpid'] = dpid
            rcd_dpid = db.findDPIDByX(dpid,'MAC_ADDR',tmp['mac'])
            tmp2['port'] = rcd_dpid[0][0]
            tmp2['ip'] = rcd_dpid[0][1].encode('utf-8')
            tmp['more'] = dict(tmp2)
            devs.append(dict(tmp))

        body = json.dumps(devs)
        return Response(content_type='application/json', body=body)

    def _dpid_list(self, req, **kwargs):
        db = database(DB_PATH)
        dpid_list = db.getDPIDLIST()
        body = json.dumps(dpid_list)
        return Response(content_type='application/json', body=body)

    def _mac(self, req, **kwargs):
        ip_addr = kwargs['ip_addr'].encode('utf-8')
        db = database(DB_PATH)
        dpid_list = db.getDPIDLIST()
        bflag = False
        info = []
        mac_addr = ''
        logined = 1
        for dpid in dpid_list:
            rcd_dpid = db.findDPIDByX(dpid,'IP_ADDR',ip_addr)
            for rcd in rcd_dpid:
                mac_addr = rcd[0].encode('utf-8')
                bflag = True
                break
            if bflag == True:
                break
        info.append(mac_addr)

        rcd_dev = db.findDEVICEByX('MAC_ADDR',mac_addr)
        if 0 == len(rcd_dev):
            logined = 0
        info.append(logined)

        body = json.dumps(info)
        return Response(content_type='application/json', body=body)

