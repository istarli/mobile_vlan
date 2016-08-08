import sys
sys.path.insert(0, './myGateway')
from myGateway import wsgi

app = wsgi.application
