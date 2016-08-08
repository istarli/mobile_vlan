import socket
import json
import sys

def socket_send(mac_addr,vlan_id,HOST='localhost',PORT=8001):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		sock.connect((HOST, PORT))
	except Exception,ex:
		err = sys.exc_info()
		info = 'Connection to [HOST:{host},PORT:{port}] failed.\n{type}:{value}'.format(host=HOST,port=PORT,type=err[0],value=err[1])
		print info
	else:
		print 'Connected to HOST:{host},PORT:{port}'.format(host=HOST,port=PORT)
		data_send = {'MAC_ADDR':mac_addr,'VLAN_ID':vlan_id}
		request = json.dumps(data_send)
		sock.send(request)
		print sock.recv(1024)
		sock.close()	
	finally:
		pass
		
if __name__ == '__main__':
	arg_num = len(sys.argv)
	HOST,PORT= 'localhost',8001
	if arg_num > 1:
		HOST = sys.argv[1]
		if arg_num > 2:
			PORT = sys.argv[2]
	print HOST,PORT
	socket_send('aaaaaa',12,HOST=HOST,PORT=PORT)

