#coding=utf-8
from django.shortcuts import render_to_response
from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext
from control.login_proc import *

import os

def hello(request):
	return HttpResponse('hello world!')

def test(request):
	return render(request,'login.html')

def login(request):
	if request.POST:
		uid = request.POST['user_id'].encode('utf-8')
		pwd = request.POST['pwd'].encode('utf-8')
		mac_addr = request.POST['mac_addr'].encode('utf-8')
		[state,info] = login_proc(uid,pwd,mac_addr,dbName='modules/USERDATA.db')
		return HttpResponse(info)
	else:
		return HttpResponse('hahaha')