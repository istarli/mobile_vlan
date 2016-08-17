# coding:utf-8
import unittest
from mobile_vlan import *

'''
To run test, change two line of the code in mobile_vlan.py first:
	line14: DB_PATH = './ryu/app/mobile_vlan/database/CONTROLLER_DATA.db' --> DB_PATH = './database/CONTROLLER_DATA.db'
	line45: init_db() --> # init_db()
'''

class TestMobileVlan(unittest.TestCase):
	def setUp(self):
		self.db = database('./database/CONTROLLER_DATA.db')
		self.db.dropDEVICE()
		self.db.createDEVICE()
		self.db.dropGATEWAY()
		self.db.createGATEWAY()
		self.db.dropMulDPID([1,2,3])
		self.db.createMulDPID([1,2,3])

	def tearDown(self):
		pass

	def test_isLogined_NS(self):
		print '\n>>>NEW_SLAVE:'
		self.db.insertGATEWAY('00:00:00:00:00:ff','10.0.0.200')
		mv = MobileVlan()
		mv.DPID_LIST=[1,2,3]
		#NEW_SLAVE, DROP
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='aaaaaa', dst_mac='bbbbbb', port_id=1, src_ip='10.0.0.1')
		self.assertEqual(mv.NEW_SLAVE,rst)
		self.assertEqual(0,rst_data['flood'])
		#NEW_SLAVE, FLOOD
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='aaaaaa', dst_mac=mv.MAC_BRO, port_id=1, src_ip='10.0.0.1')
		self.assertEqual(mv.NEW_SLAVE,rst)
		self.assertEqual(1,rst_data['flood'])
		rcd = self.db.findDPIDByX(dpid=1,x='MAC_ADDR',value='aaaaaa')
		self.assertEqual(1,len(rcd))


	def test_isLogined_NN(self):
		print '\n>>>NEW_NSLAVE:'
		self.db.insertGATEWAY('00:00:00:00:00:ff','10.0.0.200')
		mv = MobileVlan()
		mv.DPID_LIST=[1,2,3]
		#NEW_NSLAVE, DROP
		self.db.insertDPID(2,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=1)   	
		rst, rst_data= mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='bbbbbb', dst_mac='aaaaaa', port_id=1, src_ip='10.0.0.2')
		self.assertEqual(mv.NEW_NSLAVE,rst)
		self.assertEqual(0,rst_data['flood'])
		#NEW_NSLAVE, FLOOD
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='bbbbbb', dst_mac=mv.MAC_BRO, port_id=1, src_ip='10.0.0.2')
		self.assertEqual(mv.NEW_NSLAVE,rst)
		self.assertEqual(1,rst_data['flood'])
		rcd = self.db.findDPIDByX(dpid=1,x='MAC_ADDR',value='bbbbbb')
		self.assertEqual(1,len(rcd))

	def test_isLOgined_FM(self):
		print '\n>>>FAIL_MOVED:'
		self.db.insertGATEWAY('00:00:00:00:00:ff','10.0.0.200')
		mv = MobileVlan()
		mv.DPID_LIST=[1,2,3]
		#FAIL_MOVED
		self.db.insertDPID(1,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=1)
		self.db.insertDPID(2,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
		self.db.insertDPID(3,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='aaaaaa', dst_mac=mv.MAC_BRO, port_id=1, src_ip='10.0.0.1')
		self.assertEqual(mv.FAIL_MOVED,rst)
		rcd_data = self.db.findMulDPIDByX(dpid_list=[1,2,3],x='MAC_ADDR',value='aaaaaa')
		self.assertEqual(1,len(rcd_data['dpid1']))
		self.assertEqual(0,len(rcd_data['dpid2']))
		self.assertEqual(0,len(rcd_data['dpid3']))

	def test_isLogined_LG(self):
		print '\n>>>LOGINING:'
		self.db.insertGATEWAY('00:00:00:00:00:ff','10.0.0.200')
		mv = MobileVlan()
		mv.DPID_LIST=[1,2,3]
		#LOGINING
		self.db.insertDPID(1,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=1)
		self.db.insertDPID(2,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
		self.db.insertDPID(3,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
		self.db.insertDPID(1,mac_addr=mv.GATE_MAC,port_id=2,ip_addr=mv.GATE_IP,slave=0)
		self.db.insertDPID(3,mac_addr=mv.GATE_MAC,port_id=2,ip_addr=mv.GATE_IP,slave=1)
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='aaaaaa', dst_mac=mv.GATE_MAC, port_id=1, src_ip='10.0.0.1')
		self.assertEqual(mv.LOGINING,rst)
		self.assertEqual(2,rst_data['port'])	

	def test_isLogined_SM(self):
		print '\n>>>SUCCESS_MOVED:'
		self.db.insertGATEWAY('00:00:00:00:00:ff','10.0.0.200')
		mv = MobileVlan()
		mv.DPID_LIST=[1,2,3]
		#SUCCESS_MOVED, DROP
		self.db.insertDEVICE('bbbbbb',2)
		self.db.insertDPID(1,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=0)
		self.db.insertDPID(2,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.2',slave=1)
		self.db.insertDPID(3,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=0)
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='bbbbbb', dst_mac='aaaaaa',port_id=2, src_ip='10.0.0.2')
		self.assertEqual(mv.SUCCESS_MOVED,rst)
		self.assertEqual(0,rst_data['flood'])
		#SUCCESS_MOVED
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='bbbbbb', dst_mac=mv.MAC_BRO,port_id=2, src_ip='10.0.0.2')
		self.assertEqual(mv.SUCCESS_MOVED,rst)
		self.assertEqual(1,rst_data['flood'])
		self.assertEqual(2,rst_data['dpid'])
		self.assertEqual(2,rst_data['vlan'])
		rcd_data = self.db.findMulDPIDByX(dpid_list=[1,2,3],x='MAC_ADDR',value='bbbbbb')
		self.assertEqual(1,len(rcd_data['dpid1']))
		self.assertEqual(0,len(rcd_data['dpid2']))
		self.assertEqual(0,len(rcd_data['dpid3']))
		rcd_dev = self.db.findDEVICEByX(x='MAC_ADDR',value='bbbbbb')
		self.assertEqual(0,len(rcd_dev))


if __name__ == '__main__':
	unittest.main()
