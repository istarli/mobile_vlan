import urllib
import urllib2
import sys
import json

SERVER_IP = 'http://10.110.210.167:8080'

def get_ip(request):
    real_ip = ''
    try:
        real_ip = request.META['REMOTE_ADDR']
    except KeyError:
        print 'NO IP can be get.'
        return None
    else:
        real_ip = real_ip.split(",")[0]
        return real_ip


def send_req(url,content=None):
    req = url
    if None != content:
        req = urllib2.Request(url,content)
    try:
        response = urllib2.urlopen(req)
    except Exception,ex:
        err = sys.exc_info()
        info = '{type}:{value} Please check your command and the connection with controller'.format(type=err[0],value=err[1])
        print info
        return None
    else:
        return response.read()

