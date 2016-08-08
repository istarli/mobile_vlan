from database import *

def init_database(dbName='USERDATA.db'):
	db = database(dbName)
	db.dropUSER()
	db.dropDEVICE()
	db.createUSER()
	db.createDEVICE()
	db.insertUSER(2013210132,'210132',2)
	db.insertUSER(2013210133,'210133',3)
	db.insertUSER(2013210134,'210134',4)

if __name__ == '__main__':
	init_database()