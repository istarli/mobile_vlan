# coding:utf-8
import unittest
from mv_login import *

class TestMobileVlan(unittest.TestCase):
	def setUp(self):
		self.db = database('./database/CONTROLLER_DATA.db')
		self.db.dropDEVICE()
		self.db.createDEVICE()
		# self.db.insertDEVICE('aaaaaa',1)
		# self.db.insertDEVICE('bbbbbb',2)
		# self.db.insertDEVICE('cccccc',3)
		self.db.dropMulDPID([1,2,3])
		self.db.createMulDPID([1,2,3])
		# self.db.insertDPID(1,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=1)
		# self.db.insertDPID(1,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=0)
		# self.db.insertDPID(2,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
		# self.db.insertDPID(2,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=1)
		# self.db.insertDPID(3,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
		# self.db.insertDPID(3,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=0)

	def tearDown(self):
		pass

	def test_abc(self):
		self.assertTrue(1 in [1,2])
		self.assertEqual('a',"a")

	def test_isLogined_NS(self):
		mv = MobileVlan()
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
		mv = MobileVlan()
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
		mv = MobileVlan()
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
		mv = MobileVlan()
		#LOGINING
		self.db.insertDPID(1,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=1)
		self.db.insertDPID(2,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
		self.db.insertDPID(3,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='aaaaaa', dst_mac=mv.GATE_MAC)
		self.assertEqual(mv.LOGINING,rst)
		self.assertEqual(1,rst_data['toGate'])
		self.assertEqual(1,rst_data['port'])
		#LOGINING ERROR
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='aaaaaa', dst_mac='bbbbbb')
		self.assertEqual(mv.LOGINING,rst)
		self.assertEqual(0,rst_data['toGate'])		

	def test_isLogined_SM(self):
		mv = MobileVlan()
		#SUCCESS_MOVED, DROP
		self.db.insertDEVICE('bbbbbb',2)
		self.db.insertDPID(1,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=0)
		self.db.insertDPID(2,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.2',slave=1)
		self.db.insertDPID(3,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=0)
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='bbbbbb', dst_mac='aaaaaa',port_id=2, src_ip='10.0.0.2')
		self.assertEqual(mv.SUCCESS_MOVED,rst)
		self.assertEqual(0,rst_data['flood'])
		#SUCCESS_MOVED, DROP
		rst, rst_data = mv.isLogined(dpid=1, dpid_list=[1,2,3], src_mac='bbbbbb', dst_mac=mv.GATE_MAC,port_id=2, src_ip='10.0.0.2')
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
