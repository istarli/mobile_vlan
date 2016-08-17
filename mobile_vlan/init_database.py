from database.database import *

def init_db(dbName='./database/CONTROLLER_DATA.db'):
    db = database(dbName)
    dpid_list = db.getDPIDLIST()
    db.dropGATEWAY()
    db.dropDEVICE()
    db.dropMulDPID(dpid_list)
    db.createDEVICE()
    db.createGATEWAY()
    db.insertGATEWAY('00:00:00:00:00:ff','10.0.0.40')

if __name__ == '__main__':
    init_db()