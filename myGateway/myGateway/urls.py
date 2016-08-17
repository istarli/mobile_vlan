"""myGateway URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from myGateway.view import *

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^hello/$',hello),
    url(r'^test/$',test),
    url(r'^login-user/$',login_user),
    url(r'^user-login/$',user_login),
    url(r'^login-admin/$',login_admin),
    url(r'^admin-login/$',admin_login),
    url(r'^sdn-fill/$',sdn_fill),
    url(r'^admin-topo/$',admin_topo),
    url(r'^admin-table/$',admin_table),
    url(r'^admin-flow/$',admin_flow),
]
