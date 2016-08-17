import json
from my_db import get_mac
from util import SERVER_IP, send_req

PUSH_VLAN = {
    "dpid": 0,
    "table_id": 0,
    "priority": 1,
    "match":{
        "eth_src":"00:00:00:00:00:20",
        "in_port":0
    },
    "actions":[
		{
			"type":"PUSH_VLAN",
			"ethertype":33024
		},
		{
		   "type":"SET_FIELD",
		   "field": "vlan_vid",
		   "value": 4097
		},
		{
		   "type":"GOTO_TABLE",
            "table_id": 1
		}
    ],
    "mobileVlan":{
    	"MAC_ADDR":"aa",
    	"VLAN_ID":1,
    	"USER_ID":1
    }
}

VGW = [ 
    #Visit GateWay ARP
    {
        "dpid": 0,
        "vgw":"00:00:00:00:00:ff",
        "table_id": 1,
        "priority": 2,
        "match":{
            "vlan_vid": 7000,
            "arp_tpa": "10.0.0.200",
            "eth_type": 2054
        },
        "actions":[
            {
                "type":"POP_VLAN"
            },
            {
                "type":"OUTPUT",
                "port":3
            }
        ]
    },
    #Visit GateWay IP
    {
        "dpid": 0,
        "vgw":"00:00:00:00:00:ff",
        "table_id": 1,
        "priority": 2,
        "match":{
            "vlan_vid": 4097,
            "ipv4_dst": "10.0.0.200",
            "eth_type": 2048
        },
        "actions":[
            {
                "type":"POP_VLAN"
            },
            {
                "type":"OUTPUT",
                "port":3
            }
        ]
    }
]

def flow_push_vlan(url,mac_addr,vlan_id,user_id):
    flow = dict(PUSH_VLAN)
    flow['match']['eth_src'] = mac_addr
    flow['actions'][1]['value'] = 4096 + vlan_id
    flow['mobileVlan']['MAC_ADDR'] = mac_addr
    flow['mobileVlan']['VLAN_ID'] = vlan_id
    flow['mobileVlan']['USER_ID'] = user_id
    content = json.dumps(flow)
    info = send_req(url,content)
    return info

def flow_visit_gw(url,vlan_id):
    flows = list(VGW)
    info = []
    for flow in flows:
        flow['match']['vlan_vid'] = 4096 + vlan_id
        content = json.dumps(flow)
        rst = send_req(url,content)
        info.append(rst)
    return info 

def flow_login_in(ip_addr,vlan_id,user_id):
    mac_addr = get_mac(ip_addr)[0]
    url = '{cIP}/stats/flowentry/add'.format(cIP=SERVER_IP)
    info1 = flow_push_vlan(url, mac_addr, vlan_id, user_id)
    info2, info3 = flow_visit_gw(url, vlan_id)
    info = [info1, info2, info3]
    if None in [info1, info2, info3]:
        print 'Connect to controller error!'
        return None
    else:
        return info