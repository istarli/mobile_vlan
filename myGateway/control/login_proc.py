#coding=utf-8
import sys
sys.path.append('../')
from modules.database import *
from flow import flow_login_in
from my_db import get_mac

def login_proc(user_id,password,ip_addr,dbName='../modules/USERDATA.db'):
    info = ''
    db = database(dbName)
    data_set = db.findUSERByX('USER_ID',user_id)
    if 1 == len(data_set):
        pwd = data_set[0][0]
        vlan_id = data_set[0][1]
        if pwd == password:
            print 'User login in request.'
            if 0 == get_mac(ip_addr)[1]:
                if None != flow_login_in(ip_addr,vlan_id,user_id):
                    info = info + ' Login in successfully!'
                else:
                    info = info + ' Login in failed!'
            else:
                info = 'The device has logined in before! Login in failed!'
        else:
            info = 'Wrong password!'
    else:
        info = 'No this user!'
    return info
