#!/usr/bin/python
# -*- coding: utf-8 -*-
import socket,sys

dst = ('192.168.124.255',12345)
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
s.sendto("Hello",dst)
print "Looking for replies........"

while True:
    sock,addr = s.recvfrom(2048)
    if not len(sock):
        break
    print "Received from %s:%s"%(sock,addr)