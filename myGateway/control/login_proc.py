#coding=utf-8
import sys
sys.path.append('../')
# import os
from modules.database import *
from modules.init_database import *
from socketClient import *

def login_proc(user_id,password,mac_addr,dbName='../modules/USERDATA.db'):
	# print(os.getcwd())
	db = database(dbName)
	data_set = db.findUSERByX('USER_ID',user_id)
	row_num = len(data_set)
	info = ''
	state = -2
	if row_num > 1:
		info = 'Repeated user!Please check the database.'
	elif 1 == row_num:
		pwd = data_set[0][0]
		vlan_id = data_set[0][1]
		if pwd == password:
			info = 'login successfully!'
			
			socket_send(mac_addr,vlan_id,HOST='10.110.211.233')

			if 0 == len(db.findDEVICEByX('MAC_ADDR',mac_addr)):
				db.insertDEVICE(mac_addr,data_set[0][1])
				info = info + ' Update database successfully!'
			else:
				info = info + ' The device has registed before!'
			printDataSet(db.selectDEVICE())
			state = 1
		else:
			info = 'Wrong password!'
			state = 0
	else:
		info = 'No this user!'
		state = -1
	return [state,info]

if __name__ == '__main__':
	init_database(dbName='../modules/USERDATA.db')
	print(login_proc(u'2013210133'.encode('utf-8'),u'210133','aaaaaa')[1])
	print(login_proc(2013210132,'210133','bbbbbb')[1])
	print(login_proc(2013210135,'210135','cccccc')[1])