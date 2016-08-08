#coding=utf-8
import socket
import json
from database.database import *
import threading
import time
import sys

def socket_server(HOST='localhost',PORT=8001):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((HOST, PORT))
	sock.listen(5)
	print 'Serving HTTP on HOST:{host},PORT:{port} ...'.format(host=HOST,port=PORT)
	while True:
		conn, address = sock.accept()
		'''
		The code below will only be execute when server get a request. 
		'''
		print 'SocketServer:Accept a client'
		buf = conn.recv(1024)
		data_recv = json.loads(buf)
		mac_addr, vlan_id = data_recv['MAC_ADDR'].encode('utf-8'), data_recv['VLAN_ID']
		db = database('./database/CONTROLLER_DATA.db')
		if 0 == len(db.findDeviceByMac(mac_addr)):
			response = 'new device! insert to database'
			print response
			db.insertDEVICE(mac_addr,vlan_id)
			printDataSet(db.selectDEVICE()) 
		else:
			response = 'device exsisted! update database.'
			print response
			db.updateDEVICE(mac_addr,vlan_id)
			printDataSet(db.selectDEVICE())
		conn.send(response)
		conn.close()
		print 'SocketServer:Close connection.'
		
		'''
		#TODO:your task
		'''
		your_task()

def your_task():
	pass

class server_thread(threading.Thread):
	def __init__(self,HOST='localhost',PORT=8001):
		threading.Thread.__init__(self)
		self.thread_stop = False
		self.HOST = HOST
		self.PORT = PORT

	def run(self):
		while not self.thread_stop:
			socket_server(self.HOST,self.PORT)

	def stop(self):
		self.thread_stop = True

if __name__ == '__main__':
	arg_num = len(sys.argv)
	HOST,PORT= '0.0.0.0',8001
	if arg_num > 1:
		HOST = sys.argv[1]
		if arg_num > 2:
			PORT = sys.argv[2]

	st = server_thread(HOST=HOST,PORT=PORT)
	st.setDaemon(True)
	st.start()

	while True:
		time.sleep(100)