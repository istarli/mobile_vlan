#coding=utf-8
import sys
sys.path.append('../')
from modules.database import *
from flow import flow_login_in
from my_db import get_mac, get_user

def login_proc(user_id,password,ip_addr,dbName='../modules/USERDATA.db'):
    info = {}
    db = database(dbName)
    data_set = db.findUSERByX('USER_ID',user_id)
    if 1 == len(data_set):
        pwd = data_set[0][0]
        vlan_id = data_set[0][1]
        if pwd == password:
            print 'User login in request.'
            if 0 == get_mac(ip_addr)[1]:
                if None != flow_login_in(ip_addr,vlan_id,user_id):
                    info['rst'] = 'Login in successfully!'
                else:
                    info['rst'] = 'Login in failed!'
            else:
                dev_user = get_user(ip_addr)
                dev_user_id, dev_user_name = dev_user[0], dev_user[1]
                info['rst'] = 'The device has logined in before!'
                info['userid'] = 'User ID:{id}'.format(id=dev_user_id)
                info['name'] = 'User Name:{name}'.format(name=dev_user_name)
                info['state'] = 'Update Net-Info finished!'
        else:
            info['rst'] = 'Wrong password!'
    else:
        info['rst'] = 'No this user!'
    return info
