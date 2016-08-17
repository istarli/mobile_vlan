from database import *

def test_init():
    db = database()
    db.dropMulDPID([1,2,3])
    db.createMulDPID([1,2,3])
    db.insertDPID(1,mac_addr='aa:aa:aa:aa:aa:aa',port_id=1,ip_addr='10.0.0.1',slave=1)
    db.insertDPID(2,mac_addr='aa:aa:aa:aa:aa:aa',port_id=1,ip_addr='10.0.0.2',slave=0)
    db.insertDPID(2,mac_addr='bb:bb:bb:bb:bb:bb',port_id=2,ip_addr='10.0.0.2',slave=0)
    db.insertDPID(3,mac_addr='bb:bb:bb:bb:bb:bb',port_id=2,ip_addr='10.0.0.3',slave=1)

if __name__ == '__main__':
    test_init()