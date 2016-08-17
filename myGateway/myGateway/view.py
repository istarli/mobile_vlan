#coding=utf-8
from django.shortcuts import render_to_response
from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext
from control.login_proc import login_proc
from control.my_topo import analyze_topo
from control.my_db import get_table, get_flow_table
from control.util import get_ip

DB_PATH = 'modules/USERDATA.db'

def hello(request):
	return HttpResponse('hello world!')

def test(request):
	client_ip = get_ip(request)
	if None != client_ip:
		print client_ip
		return HttpResponse(client_ip)
	else:
		return HttpResponse('hello world!')
	# return HttpResponse('hello world!')

def sdn_fill(request):
	return render(request,'index.html')

def login_user(request):
	return render(request,'login_user.html')

def user_login(request):
	info = {}
	if request.POST:
		uid = request.POST['user-id'].encode('utf-8')
		pwd = request.POST['user-pw'].encode('utf-8')
		ip_addr = get_ip(request)
		info = login_proc(uid,pwd,ip_addr,dbName=DB_PATH)
	return render(request,'login_user.html', info)

def login_admin(request):
	return render(request,'login_admin.html')

def admin_login(request):
	info = {}
	if request.POST:
		uid = request.POST['admin-id'].encode('utf-8')
		pwd = request.POST['admin-pw'].encode('utf-8')
		if uid == '2233' and pwd == '2233':
			return admin_topo(request)
		else:
			info['rst'] = 'login failed.'
	return render(request,'login_admin.html', info)

def admin_topo(request):
	info_rsp = {}
	info_rsp['nodes'],info_rsp['edges'] = analyze_topo()
	return render(request,'admin_topo.html',info_rsp)

def admin_table(request):
	info_rsp = {}
	if request.POST:
		dpid = None
		order = request.POST['table-select'].encode('utf-8')
		info_rsp['order'] = order
		if 'dp' == order:
			info_rsp['dpid'] = request.POST['table-input'].encode('utf-8')
			dpid = int(info_rsp['dpid'])
		info_rsp['table'] = get_table(order,dpid)
	else:
		info_rsp['order'] = 'dev'
		info_rsp['table'] = get_table('dev')
	return render(request,'admin_table.html',info_rsp)

def admin_flow(request):
	info_rsp = {}
	if request.POST:
		dpid = None
		order = request.POST['table-select'].encode('utf-8')
		info_rsp['order'] = order
		if 'dp' == order:
			info_rsp['dpid'] = request.POST['table-input'].encode('utf-8')
			dpid = int(info_rsp['dpid'])
		info_rsp['table'] = get_flow_table(order,dpid)
	else:
		info_rsp['order'] = 'dpall'
		info_rsp['table'] = get_flow_table('dpall')
	return render(request,'admin_flow.html',info_rsp)
