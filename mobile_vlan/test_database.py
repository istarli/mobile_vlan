from database.database import *

def test_database():
	#test table DEVICE
	db = database('./database/CONTROLLER_DATA.db')
	# db.dropDEVICE()
	# db.createDEVICE()
	# db.insertDEVICE('aaaaaa',2)
	# db.insertDEVICE('bbbbbb',3)
	# db.insertDEVICE('cccccc',1)
	# printDataSet(db.selectDEVICE())
	# printDataSet(db.findDEVICEByX('MAC_ADDR','aaaaaa'))
	# db.updateDEVICE('bbbbbb',3)
	# printDataSet(db.findDEVICEByX('MAC_ADDR','aaaaaa'))

	#test table DPID
	db.dropMulDPID([1,2,3])
	db.createMulDPID([1,2,3])
	db.insertDPID(1,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.1',slave=0)
	db.insertDPID(1,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.1',slave=1)
	db.insertDPID(2,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.2',slave=0)
	db.insertDPID(2,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.2',slave=0)
	db.insertDPID(3,mac_addr='aaaaaa',port_id=1,ip_addr='10.0.0.3',slave=1)
	db.insertDPID(3,mac_addr='bbbbbb',port_id=2,ip_addr='10.0.0.3',slave=0)
	rst = db.findMulDPIDByX([1,2,3],'MAC_ADDR','aaaaaa')
	printDataSet(rst['dpid1'])
	printDataSet(rst['dpid2'])
	printDataSet(rst['dpid3'])
	print 'ok'
	db.updateDPID(1,mac_addr='aaaaaa',port_id=3,ip_addr='10.0.0.4',slave=1)
	printDataSet(db.findDPIDByX(1,'PORT_ID',3))
	print 'ok'
	db.deleteMulDPIDByX([1,2,3],x='PORT_ID',value=2)
	rst = db.selectMulDPID(dpid_list=[1,2,3])
	printDataSet(rst['dpid1'])
	printDataSet(rst['dpid2'])
	printDataSet(rst['dpid3'])
	print 'ok'


if __name__ == '__main__':
	test_database()