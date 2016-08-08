# coding=utf-8
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet
from ryu.lib.packet import packet
from ryu.ofproto import ofproto_v1_3
from database.database import *


class MobileVlan(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    #dpid_list
    DPID_LIST = []
    #device states
    NEW_SLAVE = 1
    NEW_NSLAVE = 2
    FAIL_MOVED = 3
    LOGINING = 4
    SUCCESS_MOVED = 5
    ERROR = 0
    #broadcast mac addr
    MAC_BRO = 'ff:ff:ff:ff:ff:ff'
    IP_BRO = '10.255.255.255'

    def __init__(self, *args, **kwargs):
        super(MobileVlan, self).__init__(*args, **kwargs)
        db = database('./database/CONTROLLER_DATA.db')
        self.GATE_MAC = db.selectGATEWAY()[0][0]
        self.GATE_IP = db.selectGATEWAY()[0][1]

    # 下发table-miss
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        #create table dpid in database
        db = database('./database/CONTROLLER_DATA.db')
        db.createDPID(dpid=dpid)
        self.DPID_LIST.append(dpid)
        #ovs disconnect???

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst1 = [parser.OFPInstructionGotoTable(table_id=1)]
        inst2 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        self.add_flow(datapath, 0, match, inst1)
        self.add_flow(datapath, 0, match, inst2, table_id=1)

    # 发送流表flow-mod消息(调用情况：table-miss)
    def add_flow(self, datapath, priority, match, inst, table_id=0, buffer_id=None):
        parser = datapath.ofproto_parser

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id,
                                    buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
            print "is buffer"
        else:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        datapath.send_msg(mod)
        print "is send"

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
        print "pkt**************", repr(pkt)

        # 以太网帧eth
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        print "pkt**************", repr(eth)

        dst = eth.dst
        src = eth.src

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            # 取ARP with no vlan, ad_ip, as_ip
            arp_nov = pkt.get_protocols(arp.arp)[0]
            print "arp with no vlan******************", repr(arp_nov)
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
                                    给每个ovs下发流表，删除匹配该目的mac的流表，删除匹配该目的ip的流表，删除匹配（目的ip为广播ip、vlan号）的流表;
                                    最后更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs，下发packet-out(FLOOD)
                                -->dst != MAC_BRO, DROP.(ADD FLOW?)
                6）若程序出错，则报错
            
            目的ip不是网关的情况，可能是网关回复包，也可能是未登录主机（新入网主机或移动主机）的包
            b）查询源ip是否是网关-->若不是，发送流表（匹配项为arp以太网类型、源ip、目的ip，动作丢包，软时长10s，优先级1，table-id=1）
                               -->若是，记录网关mac、ip、port信息查询ovs数据库，找到目的port，发送流表（匹配源mac、目的mac、in_port，动作output目的端口，table-id=1，软时长10s，优先级1）

            pre) 查询目的ip是否为网关，若是执行a），若不是执行b）
            '''

            if ad_ip == self.GATE_IP:
                # 目的ip是网关的情况，可能是新主机登录，也可能是移动主机登录
                # a）查询主机是否已经注册过，根据返回值选择：
                rst, rst_data = self.isLogined(dpid=dpid, dpid_list=self.DPID_LIST, src_mac=src, dst_mac=dst, port_id=in_port, src_ip=as_ip)
                if rst in [self.NEW_SLAVE,self.NEW_NSLAVE,self.FAIL_MOVED]:
                    if 1 == rst_data['flood']:
                        #TODO:FLOOD
                        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                  in_port=in_port, actions=actions, data=data)
                        datapath.send_msg(out)
                    else:
                        #TODO:DROP
                        pass
                    print "FLOOD-packet-out-when-arp-with-no-vlan-and-ovs-indirect"

                elif self.LOGINING == rst:
                    if 1 == rst_data['toGate']:
                        gate_port = rst_data['port']
                        #TODO:ADD FLOW
                        actions = [parser.OFPActionOutput(gate_port)]
                        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                        match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
                        if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                            self.add_flow(datapath, 1, match, inst, table_id=1, idle_timeout=10, buffer_id=msg.buffer_id)
                        else:
                            self.add_flow(datapath, 1, match, inst, table_id=1, idle_timeout=10)
                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                  in_port=in_port, actions=actions, data=data)
                        datapath.send_msg(out)
                        print "host is logining and we send flows"  
                    else:
                        #TODO:DROP
                        print 'host is error-logging and we pass'
                        pass              	

                elif self.SUCCESS_MOVED == rst:
                    dpid_old = rst_data['dpid']
                    vlan_old = rst_data['vlan']
                    if 1 == rst_data['flood']:

                        #TODO:DELETE MATCH FLOW
                        pass

                        # 下发packet-out(FLOOD)
                        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                        data = None
                        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                            data = msg.data
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                                  in_port=in_port, actions=actions, data=data)
                        datapath.send_msg(out)
                    else:
                        #TODO:DROP
                        pass
                    print "FLOOD-packet-out-when-arp-with-no-vlan-and-host-moved"

                else:
                	print 'Function->isLogined rst ERROR.'
            # 目的ip不是网关的情况，可能是网关回复包，也可能是未登录主机（新入网主机或移动主机）的包
            elif as_ip == self.GATE_IP:
                # 源ip是网关，this ovs 记录网关mac、ip、port信息,查询ovs数据库，找到目的port
                db = database('./database/CONTROLLER_DATA.db')
                record_gateway = db.findDPIDByX(dpid=dpid,x='MAC_ADDR',value=src)
                num_rcd_gw = len(record_gateway)
                if 0 == num_rcd_gw:
                    db.insertDPID(dpid=dpid,mac_addr=src,ip_addr=self.GATE_IP,slave=-1)
                elif 1 < num_rcd_gw:
                    print 'Database error! Repeated gateway record on dpid{dpid}!'.format(dpid=dpid)
                rcd_dpid = db.findDPIDByX(dpid=dpid,x='MAC_ADDR',value=dst)
                num_rcd_dpid = len(rcd_dpid)
                h_port = -1
                if 1 == num_rcd_dpid:
                    h_port = rcd_dpid[0][0]
                elif 0 == num_rcd_dpid:
                    print 'Datbase error: dst(mac:{mac}) has not been learnt on dpid{dpid}'.format(dpid=dpid,mac=dst)
                    return
                else:
                    print 'Database error: repeated record(mac:{mac}) on dpid{dpid}!'.format(dpid=dpid,mac=dst)
                    return

                #TODO: 发送流表（匹配源mac、目的mac、in_port，动作output目的端口，table-id=1，软时长10s，优先级1）
                actions = [parser.OFPActionOutput(h_port)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 1, match, inst, table_id=1, idle_timeout=10, buffer_id=msg.buffer_id)
                else:
                    self.add_flow(datapath, 1, match, inst, table_id=1, idle_timeout=10)
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)
                print "gateway send arp packet to host and send flows"

            else:
                # 源ip不是网关，发送流表（匹配项为arp以太网类型、源ip、目的ip，动作丢包，软时长10s，优先级1，table-id=1）
                #TODO:ADD FLOW
                actions = []
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=ad_ip, arp_spa=as_ip)
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 1, match, inst, table_id=1, idle_timeout=10, buffer_id=msg.buffer_id)
                else:
                    self.add_flow(datapath, 1, match, inst, table_id=1, idle_timeout=10)
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)
                print "no logined host visit other host and drop the arp packet"

        elif eth.ethertype == ether_types.ETH_TYPE_IP:
            db = database('./database/CONTROLLER_DATA.db')
            '''
            对于ip包，首先可以确认该包不带vlan，
            主机未登录下访问除网关外的主机时，arp包就已丢包，所以不存在该情况的ip包
            主机登录下访问其他未登录或登录主机时，应该都会带上vlan，所以这两种情况均不在此处存在
            综上，可知此处存在的情况为：主机未成功登录时，与网关之间的ip包通信;或是主机成功登录后，网关给主机发ip包
            table-id=1上传packet-in消息：
            1）获得源mac，目的mac //have got above
            2）查询ovs数据库，根据目的mac找到port作为output，发送流表（匹配源mac、目的mac、in_port，动作output，table-id=1，软时长10s，优先级1）
            '''

            record = db.findDPIDByX(dpid=dpid,x='MAC_ADDR',value=dst)
            #debug--------------------------------------------
            num_rcd = len(record)
            if 1 != num_rcd
                print 'Datbase error: dst(mac:{mac}) has not been learnt on dpid{dpid}'.format(dpid=dpid,mac=dst)
                return
            #/debug-------------------------------------------
            outport = record[0][0]
            #TODO:ADD FLOW
            pass
        elif eth.ethertype == ether_types.ETH_TYPE_8021Q:
            db = database('./database/CONTROLLER_DATA.db')
            '''
            对于vlan包，表明源主机已经成功登录且没有移动，分以下几种情况：
                  主机访问未登录主机;
                  主机访问已登录主机;
                  主机访问网关;（暂时没考虑-_-）
            该包有两种类型————带vlan的arp包和带vlan的ip包（可根据vlan字段里的ethertype来判断是arp还是ip）
            1）获得源ip、目的ip and vlan
            2）目的ip不是网关 and not brodcast
                            -->该ip在本ovs数据库中存在-->找到出端口，以及知道该ovs下是否直连目的主机
                                                                -->若直连，发送的流表多个pop动作
                                                                （匹配项vlan号、目的mac（若目的mac为广播地址，匹配项再加个目的ip））
                                                                （此处流表的下发种类需要实际测试：内容同下）
                            -->该ip在本ovs数据库中不存在-->丢包
            3）目的ip是广播ip-->查找数据库得到该vlan号对应的所有主机和port出端口，以及知道哪些主机是否直连
                                -->发送流表（匹配项vlan号、目的ip为广播ip）
                                （此处流表下发种类需要实际测试：arp包是否会匹配到这条流表，即arp包的目的ip字段能否匹配成功？？）
                                （动作有两种，对于不是直连的，直接转发;对于直连的，先pop再转发）（此处需要实际测试：两种动作能否写在同一个流表中？？）
            '''
            #TODO:GET src_ip(include as_ip),dst_ip(include ad_ip),vlan
            if dst_ip not in [self.GATE_IP,self.IP_BRO]:
                rcd = db.findDPIDByX(dpid=dpid,x='IP_ADDR',value=dst_ip)
                num_rcd = len(rcd)
                if 1 == num_rcd:
                    outport, slave = rcd[0][1], rcd[0][2]
                    if 1 == slave:#direct connect
                        #TODO:ADD FLOW WITH POP
                        pass
                    else:
                        #TODO:ADD FLOW
                        pass
                elif 0 == num_rcd:
                    #TODO:DROP
                    pass
                else:
                    print 'Database error: repeated record(ip:{ip}) on dpid{dpid}!'.format(dpid=dpid,ip=dst_ip)
                    return                    
            elif dst_ip == self.IP_BRO:
                rcd_dev = db.findDEVICEByX(x='VLAN_ID',value=vlan)
                outPorts = []
                slavePorts = []
                for x in rcd_dev:
                    rcd_dpid = db.findDPIDByX(dpid=dpid,x='MAC_ADDR',value=x[0])
                    num_rcd_dpid = len(rcd_dpid)
                    if 1 == num_rcd_dpid:
                        outPorts.append(rcd_dpid[0][0])
                        if 1 == rcd_dpid[0][2]:#slave
                            slavePorts.append(rcd_dpid[0][0])
                    elif 0 == num_rcd_dpid:
                        print 'Database error: dpid{dpid} has not learn host(mac:{mac})!'.format(dpid=dpid,mac=x[0])
                        return
                    else:
                        print 'Database error: repeated record(mac:{mac}) on dpid{dpid}!'.format(dpid=dpid,mac=x[0])
                if in_port in outPorts:
                    outPorts.remove(in_port)
                if in_port in slavePorts:
                    slavePorts.remove(in_port)
                #TODO:ADD FLOW , PACKED_OUT
            else:
                #TODO:DROP,ADD FLOW DROP
                pass
        else:
            # 忽视其他协议的包
            return

    # 判断主机是否已经注册过，根据主机源mac进行判断哦
    def isLogined(self, dpid, dpid_list, src_mac, dst_mac, port_id, src_ip):
        rst_data = {}
        db = database('./database/CONTROLLER_DATA.db')

        '''
        ovs数据库中，本ovs下是否有记录-->若有且有vlan号记录，看标签是否为0-->若是0，是移动主机 SUCCESS_MOVED
                                                                -->若是1，程序出错 ERROR
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

        record_dpid = db.findDPIDByX(dpid=dpid,x='MAC_ADDR',value=src_mac)
        num_rcd_dpid = len(record_dpid)
        dpid_list_rem = dpid_list
        dpid_list_rem.remove(dpid)
        if 0 == num_rcd_dpid:
            num_rcd_odpid = db.numMul(db.findMulDPIDByX(dpid_list=dpid_list_rem,x='MAC_ADDR',value=src_mac))
            if 0 == num_rcd_odpid:
                print 'New device,slave.'
                if self.MAC_BRO == dst_mac:
                    # 更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs
                    db.insertDPID(dpid=dpid,MAC_ADDR=src_mac,PORT_ID=port_id,IP_ADDR=src_ip,SLAVE=1)
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
                    db.insertDPID(dpid=dpid,MAC_ADDR=src_mac,PORT_ID=port_id,IP_ADDR=src_ip,SLAVE=0)
                    rst_data['flood'] = 1
                    print 'First pkt of arp. Learn and flood.'
                else:
                    rst_data['flood'] = 0
                    print 'Not first pkt of arp. Drop it.'                    
                return self.NEW_NSLAVE, rst_data
        elif 1 == num_rcd_dpid:  	
            #debug-------------------------------------
            if len(db.findMulDPIDByX(dpid_list=dpid_list,x='MAC_ADDR',value=src_mac)) != len(dpid_list):
                print 'Database error: not all ovs learned host successfully'
                return self.ERROR, rst_data
            #/debug-------------------------------------
            record_device = db.findDEVICEByX(x='MAC_ADDR',value=src_mac)
            num_rcd_dev = len(record_device)
            if 0 == num_rcd_dev:
                if self.MAC_BRO == dst_mac:
                    print 'First pkt of arp. Learn and flood.'
                    print 'Device failed log in other ovs and moved here.'
                    # 删除所有ovs中有关该ip的记录，并更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs
                    db.deleteMulDPIDByX(dpid_list=self.DPID_LIST,x='IP_ADDR',value=src_ip)
                    db.insertDPID(dpid=dpid,mac_addr=src_mac,PORT_ID=port_id,IP_ADDR=src_ip,SLAVE=1)
                    return self.FAIL_MOVED, rst_data
                else:
                    print 'Not first pkt of arp.Device is logging in.'
                    if self.GATE_MAC == dst_mac:
                        # 查询ovs数据库，找到网关port, then return
                        mac_gateway = db.selectGATEWAY()[0][0]
                        port_gateway = db.findDPIDByX(dpid=dpid,x='MAC_ADDR',value=mac_gateway)
                        rst_data['port'] = port_gateway
                        rst_data['toGate'] = 1
                    else:
                        print 'Dst_amc{mac} is not GETE_MAC, logging error.'.format(mac=dst_mac)
                        rst_data['toGate'] = 0
                    return self.LOGINING, rst_data
            elif 1 == num_rcd_dev:
                slave = record_dpid[0][2]
                if 0 == slave:
                    print 'Device has log in other ovs yet and moved here.'
                    if self.MAC_BRO == dst_mac:
                        print 'First pkt of arp. Learn and flood.'
                        rst_data['flood'] = 1
                        # 找出原来标记为直连的ovs的dpid，以及原来的vlan号;
                        record_slave = db.findMulDPIDByX(dpid_list=dpid_list_rem,x='SLAVE',value=1)
                        #debug--------------------------------------------------------
                        num = db.numMul(record_slave)
                        if 1 != num:
                            print 'Database error:Slave record error,num:{num}'.format(num=num)
                            return self.ERROR, rst_data
                        #/debug-------------------------------------------------------
                        dpid_old = -1
                        for dpidName in record_slave:
                            if 1 == len(record_slave[dpidName]):
                                dpid_old = int(dpidName[4:])

                        vlan_old = record_device[0][0]
                        rst_data['dpid'], rst_data['vlan'] = dpid_old, vlan_old

                        # 删除所有ovs数据库中有关该mac的记录，以及ryu数据库中的有关记录;
                        db.deleteMulDPIDByX(dpid_list=self.DPID_LIST,x='MAC_ADDR',value=src_mac)
                        db.deleteDEVICEByX(x='MAC_ADDR',value=src_mac)

                        # 最后更新本ovs数据库，记录主机mac、ip、port，标记该ovs为直连ovs
                        db.insertDPID(dpid=dpid,MAC_ADDR=src_mac,PORT_ID=port_id,IP_ADDR=src_ip,SLAVE=1)
                    else:
                        print 'Not first pkt of arp. Drop it.' 
                        rst_data['flood'] = 0
                    return self.SUCCESS_MOVED, rst_data
                else:
                    print 'slave==1 is expected,but slave=0.'
                    return self.ERROR, rst_data
            else:
                print 'Database error! DEVICE has repeated record! mac:{mac}'.format(mac=src_mac)
                return self.ERROR, rst_data
        else:
            print 'Database error! Repeated record:mac={mac} in dpid{dpid}!'.format(mac=src_mac,dpid=dpid)
            return self.ERROR, rst_data

if __name__ == '__main__':
    mv = MobileVlan()
    print 'ok'