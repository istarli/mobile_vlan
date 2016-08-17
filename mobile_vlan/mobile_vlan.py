# coding=utf-8
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import packet
from ryu.lib.packet import vlan
from ryu.ofproto import ofproto_v1_3
from database.database import *

DB_PATH = './ryu/app/mobile_vlan/database/CONTROLLER_DATA.db'
# DB_PATH = './database/CONTROLLER_DATA.db'

def init_db(dbName=DB_PATH):
    db = database(dbName)
    dpid_list = db.getDPIDLIST()
    db.dropGATEWAY()
    db.dropDEVICE()
    db.dropMulDPID(dpid_list)
    db.createDEVICE()
    db.createGATEWAY()
    db.insertGATEWAY('00:00:00:00:00:ff','10.0.0.200')

class MobileVlan(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    # dpid_list
    DPID_LIST = []
    # device states
    NEW_SLAVE = 1
    NEW_NSLAVE = 2
    FAIL_MOVED = 3
    LOGINING = 4
    SUCCESS_MOVED = 5
    SOVS_DPORT = 0
    # broadcast mac addr
    MAC_BRO = 'ff:ff:ff:ff:ff:ff'
    IP_BRO = '10.0.0.255'
    #outerGateway
    OG_MAC = '00:0c:29:21:04:b2'
    OG_IP = '10.0.0.254'
    OG_IP2 = '10.110.210.167'

    def __init__(self, *args, **kwargs):
        super(MobileVlan, self).__init__(*args, **kwargs)
        init_db()
        db = database(dbName=DB_PATH)
        self.GATE_MAC = db.selectGATEWAY()[0][0].encode('utf-8')
        self.GATE_IP = db.selectGATEWAY()[0][1].encode('utf-8')
        print self.GATE_IP
        self.dpset = {}
        self.mac_to_port = {}

    # 下发table-miss
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        self.dpset[dpid] = datapath
        print "new datapath*********************************************", self.dpset

        # create table dpid in database
        db = database(dbName=DB_PATH)
        db.createDPID(dpid=dpid)
        self.DPID_LIST.append(dpid)
        print self.DPID_LIST
        # ovs disconnect???

        actions1 = []
        inst1 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions1)]
        match1 = parser.OFPMatch()
        out_port = ofproto.OFPP_ANY
        out_group = ofproto.OFPG_ANY
        self.add_flow(datapath, 0, match1, inst=inst1, table_id=ofproto.OFPTT_ALL, command=3, out_port=out_port, out_group=out_group)

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst1 = [parser.OFPInstructionGotoTable(table_id=1)]
        inst2 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        self.add_flow(datapath, 0, match, inst=inst1)
        self.add_flow(datapath, 0, match, inst=inst2, table_id=1)

    # 发送流表flow-mod消息
    def add_flow(self, datapath, priority, match, inst=None, table_id=0, command=0, idle_timeout=0, buffer_id=None, out_port=0, out_group=0):
        parser = datapath.ofproto_parser

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id,
                                    command=command, idle_timeout=idle_timeout,
                                    buffer_id=buffer_id, out_port=out_port, out_group=out_group,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id,
                                    command=command, idle_timeout=idle_timeout,
                                    out_port=out_port, out_group=out_group,
                                    priority=priority, match=match,
                                    instructions=inst)
        datapath.send_msg(mod)
        print "flow is sended"

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype not in [ether_types.ETH_TYPE_ARP, ether_types.ETH_TYPE_IP, ether_types.ETH_TYPE_8021Q]:
            # print "ignore other protocols......", eth.ethertype
            return

        dst = eth.dst  # 目的mac
        src = eth.src  # 源mac

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            # 取ARP with no vlan, ad_ip, as_ip
            arp_nov = pkt.get_protocols(arp.arp)[0]
            ad_ip = arp_nov.dst_ip  # arp协议目的ip
            as_ip = arp_nov.src_ip  # arp协议源ip

            '''
            对于arp包，首先可以确认该包不带vlan，
            即可能是未注册主机的arp包，也可能是移动主机的arp包，还可能是网关的arp包，所以
            pre) 查询目的ip是否为网关，若是执行a），若不是执行b）

            目的ip是网关的情况，可能是新主机登录，也可能是移动主机登录
            a）查询主机是否已经注册过，根据返回值选择：
                1）若新机注册且直连-->dst == MAC_BRO,则更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs，下发packet-out(FLOOD)
                                -->dst != MAC_BRO, DROP.(ADD FLOW?)
                2）若新机注册且不直连-->dst == MAC_BRO,则更新本ovs数据库，记录主机mac、ip、port，标记该ovs为不直连ovs，下发packet-out(FLOOD)
                                  -->dst != MAC_BRP,DROP.(ADD FLOW?)
            （新）3）若主机未成功登录且移动，则删除所有ovs中有关该ip的记录，并更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs，下发packet-out(FLOOD)
                4）若主机正处于登录过程，则查询ovs数据库，找到网关port，发送流表（匹配源mac、目的mac、in_port，动作output网关端口，table-id=1，软时长10s，优先级1）
                5）若主机是移动主机-->dst == MAC_BRO，
                                    则找出原来标记为直连的ovs的dpid，以及原来的vlan号;
                                    删除所有ovs数据库中有关该mac的记录，以及ryu数据库中的有关记录;
                                    给之前的直连ovs下发流表，删除匹配该源mac的流表;
                                    给每个ovs下发流表，删除匹配该目的mac的流表，删除匹配该yuan mac的流表，删除匹配该目的ip的流表，删除匹配（目的ip为广播ip、vlan号）的流表;
                                    最后更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs，下发packet-out(FLOOD)
                                -->dst != MAC_BRO, DROP.(ADD FLOW?)
                6）若程序出错，则报错

            目的ip不是网关的情况，可能是网关回复包，也可能是未登录主机（新入网主机或移动主机）的包
            b）查询源ip是否是网关-->若不是，发送流表（匹配项为arp以太网类型、源ip、目的ip，动作丢包，软时长10s，优先级1，table-id=1）
                               -->若是，记录网关mac、ip、port信息查询ovs数据库，找到目的port，发送流表（匹配源mac、目的mac、in_port，动作output目的端口，table-id=1，软时长10s，优先级1）

            pre) 查询目的ip是否为网关，若是执行a），若不是执行b）
            '''
            if self.OG_IP != ad_ip and self.OG_IP != as_ip:
                if self.OG_MAC == src:
                    return
                else:
                    print "\nFROM DPID:",dpid
                    print "pkt**************", repr(pkt)
                    print "eth**************", repr(eth)

                if ad_ip == self.GATE_IP:
                    # 目的ip是网关的情况，可能是新主机登录，也可能是移动主机登录,or outerGate
                    #filter outerGate
                    # a）查询主机是否已经注册过，根据返回值选择：
                    rst, rst_data = self.isLogined(dpid=dpid, dpid_list=self.DPID_LIST, src_mac=src, dst_mac=dst,
                                                   port_id=in_port, src_ip=as_ip)
                    if rst in [self.NEW_SLAVE, self.NEW_NSLAVE, self.FAIL_MOVED]:
                        if 1 == rst_data['flood']:
                            # TODO:FLOOD
                            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                            data = None
                            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                                data = msg.data
                            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                      in_port=in_port, actions=actions, data=data)
                            datapath.send_msg(out)
                            print "FLOOD-packet-out-when-arp-with-no-vlan-and-ovs-indirect"
                        else:
                            # TODO:DROP
                            return

                    elif self.LOGINING == rst:
                        # if 1 == rst_data['toGate']:
                        gate_port = rst_data['port']
                        # TODO:ADD FLOW
                        # 发送流表（匹配源mac、目的mac、in_port，动作output网关端口，table-id=1，软时长10s，优先级1）
                        actions = [parser.OFPActionOutput(gate_port)]
                        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                        match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
                        if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                            self.add_flow(datapath, 1, match, inst=inst, table_id=1, idle_timeout=1000, buffer_id=msg.buffer_id)
                        else:
                            self.add_flow(datapath, 1, match, inst=inst, table_id=1, idle_timeout=1000)
                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                  in_port=in_port, actions=actions, data=data)
                        datapath.send_msg(out)
                        print "host is logining and we send flows"
                        # else:
                        #     #TODO: DROP
                        #     print 'host is error-logging and we pass'
                        #     return 

                    elif self.SUCCESS_MOVED == rst:
                        # dpid_old = rst_data['dpid']
                        vlan_old = rst_data['vlan']
                        if 1 == rst_data['flood']:

                            # TODO:DELETE MATCH FLOW
                            '''
                            # 给之前的直连ovs下发流表，删除匹配该源mac的流表;
                            dp_old = self.dpset[dpid_old]
                            ofp_old = dp_old.ofproto
                            pars_old = dp_old.ofproto_parser

                            actions = []
                            inst = [pars_old.OFPInstructionActions(ofp_old.OFPIT_APPLY_ACTIONS, actions)]
                            match = pars_old.OFPMatch(eth_src=src)
                            out_port = ofp_old.OFPP_ANY
                            out_group = ofp_old.OFPG_ANY
                            self.add_flow(dp_old, 1, match, inst=inst, table_id=ofp_old.OFPTT_ALL, command=3, idle_timeout=1000,
                                          out_port=out_port, out_group=out_group)
                            '''

                            # 给每个ovs下发流表，删除匹配该目的mac的流表，删除匹配该目的ip的流表，删除匹配该yuan mac的流表，删除匹配（目的ip为广播ip、vlan号）的流表;
                            for x in self.dpset:
                                print "when host moved, begin to delete flows......"
                                print "dpid: ", x
                                dp_iter = self.dpset[x]
                                ofp_iter = dp_iter.ofproto
                                pars_iter = dp_iter.ofproto_parser
                                actions = []
                                inst = [pars_iter.OFPInstructionActions(ofp_iter.OFPIT_APPLY_ACTIONS, actions)]
                                # 删除匹配该目的mac的流表
                                match1 = pars_iter.OFPMatch(eth_dst=src)
                                # 删除匹配该目的ip的流表
                                match2 = pars_iter.OFPMatch(arp_tpa=as_ip, eth_type=ether_types.ETH_TYPE_ARP)
                                # match3 = pars_iter.OFPMatch(ipv4_dst=as_ip, eth_type=ether_types.ETH_TYPE_IP)
                                # 删除匹配该yuan mac的流表
                                match3 = pars_iter.OFPMatch(eth_src=src)
                                # 删除匹配（目的ip为广播ip、vlan号）的流表
                                match4 = pars_iter.OFPMatch(vlan_vid=(0x1000 | vlan_old), ipv4_dst=self.IP_BRO, eth_type=ether_types.ETH_TYPE_IP)
                                out_port_iter = ofp_iter.OFPP_ANY
                                out_group_iter = ofp_iter.OFPG_ANY
                                self.add_flow(dp_iter, 1, match1, inst=inst, table_id=ofp_iter.OFPTT_ALL, command=3, idle_timeout=1000,
                                              out_port=out_port_iter, out_group=out_group_iter)
                                self.add_flow(dp_iter, 1, match2, inst=inst, table_id=ofp_iter.OFPTT_ALL, command=3, idle_timeout=1000,
                                              out_port=out_port_iter, out_group=out_group_iter)
                                self.add_flow(dp_iter, 1, match3, inst=inst, table_id=ofp_iter.OFPTT_ALL, command=3, idle_timeout=1000,
                                              out_port=out_port_iter, out_group=out_group_iter)
                                self.add_flow(dp_iter, 1, match4, inst=inst, table_id=ofp_iter.OFPTT_ALL, command=3, idle_timeout=1000,
                                              out_port=out_port_iter, out_group=out_group_iter)

                            # 下发packet-out(FLOOD)
                            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                            data = None
                            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                                data = msg.data
                            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                      in_port=in_port, actions=actions, data=data)
                            datapath.send_msg(out)
                        else:
                            # TODO:DROP
                            return
                        print "FLOOD-packet-out-when-arp-with-no-vlan-and-host-moved"
                    elif self.SOVS_DPORT == rst:
                        # the host moved to the same ovs and different port
                        # 主机移动到同一ovs的不同端口下：（可能会访问网关，也可能访问其他主机，所有的数据库只有本ovs下需要修改）
                        # 更新本ovs下的数据库，将该主机（已知mac地址src）的port端口改为新端口in_port，
                        # 获取本主机的vlan号v_vid
                        # 删除本ovs下的四大流表，
                        # 下发新的pushvlan流表到table-id=0并且go to table_id=1
                        # Packet-out

                        # 更新本ovs下的数据库，将该主机（已知mac地址src）的port端口改为新端口in_port
                        db = database(DB_PATH)
                        db.updateDPID(dpid=dpid, mac_addr=src, port_id=in_port, ip_addr=as_ip, slave=1)
                        # 获取本主机的vlan号v_vid
                        v_vid = db.findDEVICEByX(x='MAC_ADDR',value=src)[0][0]
                        
                        # 删除本ovs下的四大流表，
                        actions1 = []
                        inst1 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions1)]
                        # 删除匹配该目的mac的流表
                        match1 = parser.OFPMatch(eth_dst=src)
                        # 删除匹配该目的ip的流表
                        match2 = parser.OFPMatch(arp_tpa=as_ip, eth_type=ether_types.ETH_TYPE_ARP)
                        # match3 = parser.OFPMatch(ipv4_dst=as_ip, eth_type=ether_types.ETH_TYPE_IP)
                        # 删除匹配该yuan mac的流表
                        match3 = parser.OFPMatch(eth_src=src)
                        # 删除匹配（目的ip为广播ip、vlan号）的流表
                        match4 = parser.OFPMatch(vlan_vid=(0x1000 | v_vid), ipv4_dst=self.IP_BRO, eth_type=ether_types.ETH_TYPE_IP)
                        out_port = ofproto.OFPP_ANY
                        out_group = ofproto.OFPG_ANY
                        self.add_flow(datapath, 1, match1, inst=inst1, table_id=ofproto.OFPTT_ALL, command=3, idle_timeout=1000,
                                      out_port=out_port, out_group=out_group)
                        self.add_flow(datapath, 1, match2, inst=inst1, table_id=ofproto.OFPTT_ALL, command=3, idle_timeout=1000,
                                      out_port=out_port, out_group=out_group)
                        self.add_flow(datapath, 1, match3, inst=inst1, table_id=ofproto.OFPTT_ALL, command=3, idle_timeout=1000,
                                      out_port=out_port, out_group=out_group)
                        self.add_flow(datapath, 1, match4, inst=inst1, table_id=ofproto.OFPTT_ALL, command=3, idle_timeout=1000,
                                      out_port=out_port, out_group=out_group)
                        # 下发新的pushvlan流表到table-id=0并且go to table_id=1
                        # Packet-out
                        match = parser.OFPMatch(eth_src=src, in_port=in_port)
                        actions = [parser.OFPActionPushVlan(), parser.OFPActionSetField(vlan_vid=(0x1000 | v_vid))]
                        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions), 
                                parser.OFPInstructionGotoTable(table_id=1)]
                        if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                            self.add_flow(datapath, 1, match, inst=inst, table_id=0, buffer_id=msg.buffer_id)
                        else:
                            self.add_flow(datapath, 1, match, inst=inst, table_id=0)
                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
                        datapath.send_msg(out)
                        print "the host moved to the same ovs and different port"
                    else:
                        print 'Function->isLogined rst ERROR.'
                # 目的ip不是网关的情况，可能是网关回复包，也可能是未登录主机（新入网主机或移动主机）的包
                elif as_ip == self.GATE_IP:
                    # 源ip是网关，this ovs 记录网关mac、ip、port信息,查询ovs数据库，找到目的port
                    db = database(dbName=DB_PATH)
                    record_gateway = db.findDPIDByX(dpid=dpid, x='MAC_ADDR', value=src)
                    if 0 == len(record_gateway):#not learnt gateway
                        slave = 1
                        dplist_rem = list(self.DPID_LIST)
                        dplist_rem.remove(dpid)
                        rcd_dplist = db.findMulDPIDByX(dplist_rem,'MAC_ADDR',src)
                        for dpidName in rcd_dplist:
                            for rcd in rcd_dplist[dpidName]:
                                if 0 != len(rcd):
                                    slave = 0
                                    break
                        db.insertDPID(dpid=dpid, mac_addr=src, port_id=in_port, ip_addr=self.GATE_IP, slave=slave)

                    h_port = -1
                    rcd_dpid = db.findDPIDByX(dpid=dpid, x='MAC_ADDR', value=dst)
                    if 1 == len(rcd_dpid):
                        h_port = rcd_dpid[0][0]
                    else:
                        print 'Datbase error: dst(mac:{mac}) has not been learnt on dpid{dpid}'.format(dpid=dpid, mac=dst)
                        return

                    # TODO: 发送流表（匹配源mac、目的mac、in_port，动作output目的端口，table-id=1，软时长100s，优先级1）
                    actions = [parser.OFPActionOutput(h_port)]
                    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                    match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=1, idle_timeout=1000, buffer_id=msg.buffer_id)
                    else:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=1, idle_timeout=1000)
                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                              in_port=in_port, actions=actions, data=data)
                    datapath.send_msg(out)
                    print "gateway send arp packet to host and send flows"

                else:
                    # 源ip不是网关，发送流表（匹配项为arp以太网类型、源ip、目的ip，动作丢包，软时长10s，优先级1，table-id=1）
                    # TODO:ADD FLOW
                    actions = []
                    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                    match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=ad_ip, arp_spa=as_ip)
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=1, idle_timeout=1000, buffer_id=msg.buffer_id)
                    else:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=1, idle_timeout=1000)
                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                              in_port=in_port, actions=actions, data=data)
                    datapath.send_msg(out)
                    print "no logined host visit other host and drop the arp packet"
            else:
                # simple_switch_13
                self.mac_to_port.setdefault(dpid, {})
                # learn a mac address to avoid FLOOD next time.
                self.mac_to_port[dpid][src] = in_port
                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                else:
                    out_port = ofproto.OFPP_FLOOD
                actions = [parser.OFPActionOutput(out_port)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                # install a flow to avoid packet_in next time
                if out_port != ofproto.OFPP_FLOOD:
                    match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
                    # verify if we have a valid buffer_id, if yes avoid to send both
                    # flow_mod & packet_out
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=0, buffer_id=msg.buffer_id)
                    else:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=0)
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)

        elif eth.ethertype == ether_types.ETH_TYPE_IP:
            # 取IP with no vlan, id_ip, is_ip
            ip_nov = pkt.get_protocols(ipv4.ipv4)[0]
            id_ip = ip_nov.dst  # ip协议目的ip
            is_ip = ip_nov.src  # ip协议源ip

            if self.OG_IP2 != id_ip and self.OG_IP2 != is_ip:

                if self.GATE_MAC == dst or self.GATE_MAC == src:
                    print "\nFROM DPID:",dpid
                    print "pkt**************", repr(pkt)
                    print "eth**************", repr(eth)

                    db = database(dbName=DB_PATH)
                    '''
                    对于ip包，首先可以确认该包不带vlan，
                    主机未登录下访问除网关外的主机时，arp包就已丢包，所以不存在该情况的ip包
                    主机登录下访问其他未登录或登录主机时，应该都会带上vlan，所以这两种情况均不在此处存在
                    综上，可知此处存在的情况为：主机未成功登录时，与网关之间的ip包通信;或是主机成功登录后，网关给主机发ip包
                    table-id=1上传packet-in消息：
                    1）获得源mac，目的mac //have got above
                    2）查询ovs数据库，根据目的mac找到port作为output，发送流表（匹配源mac、目的mac、in_port，动作output，table-id=1，软时长10s，优先级1）
                    '''

                    record = db.findDPIDByX(dpid=dpid, x='MAC_ADDR', value=dst)
                    # debug--------------------------------------------
                    num_rcd = len(record)
                    if 1 != num_rcd:
                        print 'Datbase error: dst(mac:{mac}) has not been learnt on dpid{dpid}'.format(dpid=dpid, mac=dst)
                        return
                    # /debug-------------------------------------------
                    outport = record[0][0]
                    # TODO:ADD FLOW
                    actions = [parser.OFPActionOutput(outport)]
                    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                    match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=1, idle_timeout=1000, buffer_id=msg.buffer_id)
                    else:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=1, idle_timeout=1000)
                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                              in_port=in_port, actions=actions, data=data)
                    datapath.send_msg(out)
                    print "when ip protocol with no vlan, send flows"
                else:
                    return
            else:
                # simple_switch_13
                self.mac_to_port.setdefault(dpid, {})
                # learn a mac address to avoid FLOOD next time.
                self.mac_to_port[dpid][src] = in_port
                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                else:
                    out_port = ofproto.OFPP_FLOOD
                actions = [parser.OFPActionOutput(out_port)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                # install a flow to avoid packet_in next time
                if out_port != ofproto.OFPP_FLOOD:
                    match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
                    # verify if we have a valid buffer_id, if yes avoid to send both
                    # flow_mod & packet_out
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=0, buffer_id=msg.buffer_id)
                    else:
                        self.add_flow(datapath, 1, match, inst=inst, table_id=0)
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)

        elif eth.ethertype == ether_types.ETH_TYPE_8021Q:
            print '\nFROM DPID{dpid}:'.format(dpid=dpid)
            print "pkt**************", repr(pkt)
            db = database(dbName=DB_PATH)
            '''
            对于vlan包，表明源主机已经成功登录且没有移动，分以下几种情况：
                  主机访问未登录主机;
                  主机访问已登录主机;
                  主机访问网关;
            该包有两种类型————带vlan的arp包和带vlan的ip包（可根据vlan字段里的ethertype来判断是arp还是ip）
            1）获得源ip、目的ip and vlan
            2）目的ip不是网关 and not brodcast
                            -->该ip在本ovs数据库中存在 and vlan equal-->找到出端口，以及知道该ovs下是否直连目的主机
                                                                -->若直连，发送的流表多个pop动作
                                                                （匹配项vlan号、目的mac（若目的mac为广播地址，匹配项再加个目的ip））
                                                                （此处流表的下发种类需要实际测试：内容同下）
                            -->该ip在本ovs数据库中不存在 or vlan not equal-->丢包
            3）目的ip是广播ip-->查找数据库得到该vlan号对应的所有主机和port出端口，以及知道哪些主机是否直连
                                -->发送流表（匹配项vlan号、目的ip为广播ip）
                                （此处流表下发种类需要实际测试：arp包是否会匹配到这条流表，即arp包的目的ip字段能否匹配成功？？）
                                （动作有两种，对于不是直连的，直接转发;对于直连的，先pop再转发）（此处需要实际测试：两种动作能否写在同一个流表中？？）
            4) 目的ip是网关
            '''
            # TODO:GET src_ip(include as_ip),dst_ip(include ad_ip),v_vid
            # 取vlan包, v_type, v_vid,
            vlan_pkt = pkt.get_protocols(vlan.vlan)[0]
            print "vlan packet******************", repr(vlan_pkt)
            v_type = vlan_pkt.ethertype  # vlan的下一个协议（arp或ip）
            v_vid = vlan_pkt.vid  # vlan号
            if v_type == ether_types.ETH_TYPE_ARP:
                v_arp = pkt.get_protocols(arp.arp)[0]
                print "vlan packet of arp******************", repr(v_arp)
                dst_ip = v_arp.dst_ip
                src_ip = v_arp.src_ip
            elif v_type == ether_types.ETH_TYPE_IP:
                v_ip = pkt.get_protocols(ipv4.ipv4)[0]
                print "vlan packet of ipv4******************", repr(v_ip)
                dst_ip = v_ip.dst
                src_ip = v_ip.src
            else:
                print "error!! vlan packet with neither arp nor ipv4 protocols......"
                dst_ip = "0.0.0.0"
                src_ip = "0.0.0.0"

            if dst_ip not in [self.GATE_IP, self.IP_BRO]:
                rcd_src = db.findDEVICEByX(x='MAC_ADDR',value=src)
                if self.MAC_BRO != dst:
                    rcd_dst = db.findDEVICEByX(x='MAC_ADDR',value=dst)
                    if len(rcd_dst) == 0:
                        print 'dst host has not login in,drop.'
                        return
                    elif rcd_dst[0][0] != rcd_src[0][0]:
                        print 'dst and src are in different vlan,drop.'
                        return

                rcd = db.findDPIDByX(dpid=dpid, x='IP_ADDR', value=dst_ip)
                num_rcd = len(rcd)
                if 1 == num_rcd:
                    outport, slave = rcd[0][1], rcd[0][2]
                    if 1 == slave:  # direct connect
                        # 若直连，发送的流表多个pop动作（匹配项vlan号、目的mac（若目的mac为广播地址，匹配项再加个目的ip））
                        # TODO:ADD FLOW WITH POP
                        if dst != self.MAC_BRO:
                            actions = [parser.OFPActionPopVlan(), parser.OFPActionOutput(outport)]
                            match = parser.OFPMatch(vlan_vid=(0x1000 | v_vid), eth_dst=dst)
                        else:
                            actions = [parser.OFPActionPopVlan(), parser.OFPActionOutput(outport)]
                            match = parser.OFPMatch(vlan_vid=(0x1000 | v_vid), eth_dst=dst, arp_tpa=dst_ip, eth_type=ether_types.ETH_TYPE_ARP)
                    else:
                        # TODO:ADD FLOW
                        if dst != self.MAC_BRO:
                            actions = [parser.OFPActionOutput(outport)]
                            match = parser.OFPMatch(vlan_vid=(0x1000 | v_vid), eth_dst=dst)
                        else:
                            actions = [parser.OFPActionOutput(outport)]
                            match = parser.OFPMatch(vlan_vid=(0x1000 | v_vid), eth_dst=dst, arp_tpa=dst_ip, eth_type=ether_types.ETH_TYPE_ARP)
                    # 下发流表
                    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 2, match, inst=inst, table_id=1, idle_timeout=9999,
                                      buffer_id=msg.buffer_id)
                    else:
                        self.add_flow(datapath, 2, match, inst=inst, table_id=1, idle_timeout=9999)
                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                              in_port=in_port, actions=actions, data=data)
                    datapath.send_msg(out)
                    print "vlan packet: when dst_ip not gateway and not broadcast, send flows"

                elif 0 == num_rcd:
                    # print 'Database error: dst({ip}) has login in but was not learnt by dpid{dpid}!'.format(dpid=dpid, ip=dst_ip)
                    # TODO:DROP
                    actions = []
                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                              in_port=in_port, actions=actions, data=data)
                    datapath.send_msg(out)
                    print "vlan packet: when dst_ip not logined, drop"
                else:
                    print 'Database error: repeated record(ip:{ip}) on dpid{dpid}!'.format(dpid=dpid, ip=dst_ip)
                    return

            elif dst_ip == self.IP_BRO:
                rcd_dev = db.findDEVICEByX(x='VLAN_ID', value=v_vid)
                outPorts = []
                slavePorts = []
                for x in rcd_dev:
                    rcd_dpid = db.findDPIDByX(dpid=dpid, x='MAC_ADDR', value=x[0].encode('utf-8'))
                    num_rcd_dpid = len(rcd_dpid)
                    if 1 == num_rcd_dpid:
                        dst_port = rcd_dpid[0][0]
                        isSlave = rcd_dpid[0][2]
                        if in_port != dst_port:
                            if 1 == isSlave:  # slave
                                slavePorts.append(dst_port)
                            else:
                                outPorts.append(dst_port)
                    elif 0 == num_rcd_dpid:
                        print 'Database error: dpid{dpid} has not learn host(mac:{mac})!'.format(dpid=dpid, mac=x[0])
                        return
                    else:
                        print 'Database error: repeated record(mac:{mac}) on dpid{dpid}!'.format(dpid=dpid, mac=x[0])
                        return

                print outPorts
                print slavePorts

                # TODO:ADD FLOW , PACKED_OUT
                # -->发送流表（匹配项vlan号、目的ip为广播ip）
                match = parser.OFPMatch(vlan_vid=(0x1000 | v_vid), ipv4_dst=self.IP_BRO, eth_type=ether_types.ETH_TYPE_IP)

                actions1 = []
                for x in outPorts:
                    actions1.append(parser.OFPActionOutput(x))
                inst1 = [parser.OFPInstructionGotoTable(table_id=2), parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions1)]

                actions2 = [parser.OFPActionPopVlan()]
                for y in slavePorts:
                    actions2.append(parser.OFPActionOutput(y))
                inst2 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions2)]

                self.add_flow(datapath, 2, match, inst=inst2, table_id=2, idle_timeout=9999)
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 2, match, inst=inst1, table_id=1, idle_timeout=9999, buffer_id=msg.buffer_id)
                else:
                    self.add_flow(datapath, 2, match, inst=inst1, table_id=1, idle_timeout=9999)
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions1, data=data)
                datapath.send_msg(out)
                print "vlan packet: when ip is broadcast, send flows"
            else:
                # 目的ip是网关，说明主机登录成功后再次访问网关
                # 匹配（vlan号，目的ip），存在时长为永久，动作（找该ovs的数据库，知道网关的g_port，作为output的port），table-id为1，优先级1
                g_port = db.findDPIDByX(dpid=dpid, x='MAC_ADDR', value=self.GATE_MAC)[0][0]

                match1 = parser.OFPMatch(vlan_vid=(0x1000 | v_vid), arp_tpa=dst_ip, eth_type=ether_types.ETH_TYPE_ARP)
                match2 = parser.OFPMatch(vlan_vid=(0x1000 | v_vid), ipv4_dst=dst_ip, eth_type=ether_types.ETH_TYPE_IP)
                actions = [parser.OFPActionOutput(g_port)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                self.add_flow(datapath, 1, match1, inst=inst, table_id=1)
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)
                print "vlan packet: when ip is gateway, send flows"
        else:
            # 忽视其他协议的包
            return

    # 判断主机是否已经注册过，根据主机源mac进行判断哦
    def isLogined(self, dpid, dpid_list, src_mac, dst_mac, port_id, src_ip):
        rst_data = {}
        db = database(dbName=DB_PATH)

        '''
        ovs数据库中，本ovs下是否有记录-->若有且有vlan号记录，看标签是否为0-->若是0，是移动主机 SUCCESS_MOVED
                                                                -->若是1，the host moved to the same ovs and different port
                                   -->若有且无vlan号记录，可能主机未成功登录且移动，或者是正处于登录过程（S二者区别在于目的mac是否为广播mac）
                                                       看目的mac-->若是广播mac，则主机未成功登录且移动 FAIL_MOVED
                                                               -->若是GATE_MAC，则正处于登录过程 LOGINING
                                                               -->other mac,drop             LOGINING
                                   -->若无，其他ovs上是否有记录-->若有，是新注册且不直连主机 NEW_NSLAVE
                                                            -->若无，是新注册且直连主机 NEW_SLAVE
        返回值：1：新机注册且直连 NEW_SLAVE
               2：新机注册且不直连 NEW_NSLAVE
               3：主机未成功登录且移动 FAIL_MOVED
               4：主机正处于登录过程（每个ovs已有数据库） LOGINING
               5：主机成功登录且移动 SUCCESS_MOVED
               0：程序出错 ERROR
        '''

        record_dpid = db.findDPIDByX(dpid=dpid, x='MAC_ADDR', value=src_mac)
        dpid_list_rem = list(dpid_list)
        dpid_list_rem.remove(dpid)

        if 0 == len(record_dpid):
            num_rcd_odpid = db.numMul(db.findMulDPIDByX(dpid_list=dpid_list_rem, x='MAC_ADDR', value=src_mac))
            if 0 == num_rcd_odpid:
                print 'New device,slave.'
                if self.MAC_BRO == dst_mac:
                    # 更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs
                    db.insertDPID(dpid=dpid, mac_addr=src_mac, port_id=port_id, ip_addr=src_ip, slave=1)
                    rst_data['flood'] = 1
                    print 'First pkt of arp. Learn and flood.'
                else:
                    rst_data['flood'] = 0
                    print 'Not first pkt of arp. Drop it.'
                return self.NEW_SLAVE, rst_data
            else:
                print 'New device, not slave.'
                if self.MAC_BRO == dst_mac:
                    # 更新本ovs数据库，记录主机mac、ip、port，标记该ovs为不直连ovs
                    db.insertDPID(dpid=dpid, mac_addr=src_mac, port_id=port_id, ip_addr=src_ip, slave=0)
                    rst_data['flood'] = 1
                    print 'First pkt of arp. Learn and flood.'
                else:
                    rst_data['flood'] = 0
                    print 'Not first pkt of arp. Drop it.'
                return self.NEW_NSLAVE, rst_data
        else:
            record_device = db.findDEVICEByX(x='MAC_ADDR', value=src_mac)
            if 0 == len(record_device):
                if self.MAC_BRO == dst_mac:
                    print 'First pkt of arp. Learn and flood.'
                    print 'Device failed log in other ovs and moved here.'
                    # 删除所有ovs中有关该ip的记录，并更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs
                    db.deleteMulDPIDByX(dpid_list=self.DPID_LIST, x='IP_ADDR', value=src_ip)
                    db.insertDPID(dpid=dpid, mac_addr=src_mac, port_id=port_id, ip_addr=src_ip, slave=1)
                    return self.FAIL_MOVED, rst_data
                else:
                    print 'Not first pkt of arp.Device is logging in.'
                    # 查询ovs数据库，找到网关port, then return
                    mac_gateway = db.selectGATEWAY()[0][0].encode('utf-8')
                    port_gateway = db.findDPIDByX(dpid=dpid, x='MAC_ADDR', value=mac_gateway)[0][0]
                    rst_data['port'] = port_gateway
                    return self.LOGINING, rst_data
            else:
                slave = record_dpid[0][2]
                if 0 == slave:
                    print 'Device has log in other ovs yet and moved here.'
                    if self.MAC_BRO == dst_mac:
                        print 'First pkt of arp. Learn and flood.'
                        rst_data['flood'] = 1
                        # 找出原来标记为直连的ovs的dpid，以及原来的vlan号;
                        rcd_src = db.findMulDPIDByX(dpid_list=dpid_list_rem, x='MAC_ADDR', value=src_mac)
                        dpid_old = -1
                        for x in rcd_src:
                            if 1 == rcd_src[x][0][2]:
                                dpid_old = int(x[4:])
                                break

                        vlan_old = record_device[0][0]
                        rst_data['dpid'], rst_data['vlan'] = dpid_old, vlan_old
                        # 删除所有ovs数据库中有关该mac的记录，以及ryu数据库中的有关记录;
                        db.deleteMulDPIDByX(dpid_list=self.DPID_LIST, x='MAC_ADDR', value=src_mac)
                        db.deleteDEVICEByX(x='MAC_ADDR', value=src_mac)
                        # 最后更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs
                        db.insertDPID(dpid=dpid, mac_addr=src_mac, port_id=port_id, ip_addr=src_ip, slave=1)
                    else:
                        print 'Not first pkt of arp. Drop it.'
                        rst_data['flood'] = 0
                    return self.SUCCESS_MOVED, rst_data
                else:
                    print 'The device removed to other port of the same ovs.'
                    return self.SOVS_DPORT, rst_data