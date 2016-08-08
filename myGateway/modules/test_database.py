from database import *

def test_db():
	db = database()
	db.dropUSER()
	db.dropDEVICE()
	db.createUSER()
	db.createDEVICE()
	db.insertUSER(2013210132,'210132',2)
	db.insertUSER(2013210133,'210133',3)
	db.insertUSER(2013210134,'210134',4)
	db.insertDEVICE('aaaaaa',2013210132)
	db.insertDEVICE('bbbbbb',2013210133)
	printDataSet(db.findUSERByX('USER_ID',2013210133))
	db.deleteUSERByX('VLAN_ID',2)
	printDataSet(db.findUSERByX('USER_ID',2013210132))

	printDataSet(db.findDEVICEByX('USER_ID',2013210133))
	db.deleteDEVICEByX('MAC_ADDR','aaaaaa')
	printDataSet(db.findDEVICEByX('USER_ID',2013210132))

	return

if __name__ == '__main__':
	test_db()
