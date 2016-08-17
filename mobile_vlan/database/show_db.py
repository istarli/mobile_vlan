from database import *

def show_db():
    db = database()
    print 'TABLE_GATEWAY:'
    printDataSet(db.selectGATEWAY())
    print '\nTABLE_DEVICE:'
    printDataSet(db.selectDEVICE())
    
    dpid_list = db.getDPIDLIST()
    for dpid in dpid_list:
        print '\nTABLE_DPID{dpid}'.format(dpid=dpid)
        printDataSet(db.selectDPID(dpid))

if __name__ == '__main__':
    show_db()