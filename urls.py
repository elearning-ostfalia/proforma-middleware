"""proforma URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, re_path
from django.contrib import admin
from django.urls import path
from taskget import views as v
from api import views

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^grade/(?P<lms>[a-zA-Z\_\.\d]{3,32})/(?P<lms_version>\d{1,6})/(?P<language>[a-zA-Z\_\.\d]{3,32})/'
       r'(?P<language_version>\d{1,6})/(?P<textfield_or_file>[a-zA-Z\_\.\d]{4,9})$'
       r'', views.grade_api_v1, name="grade"),
    re_path(r'^grade/(?P<lms>[a-zA-Z\_\.\d]{3,32})/(?P<lms_version>\d{1,6})/(?P<language>[a-zA-Z\_\.\d]{3,32})/'
       r'(?P<textfield_or_file>[a-zA-Z\_\.\d]{4,9})$'
       r'', views.grade_api_v1, name="grade"),
    re_path(r'^api/v1/grading/prog-languages/(?P<fw>[a-zA-Z\_\.\d]{3,32})/(?P<fw_version>\d{1,6})/submissions$'
       r'', views.grade_api_v1, name="grade_api_v1"),
    re_path(r'^api/v1/repositories$', views.list_repo, name="list_repo"),
    re_path(r'^VERSION$', views.get_version, name="get_version"),
    re_path(r'^api/v2/submissions$', views.grade_api_v2, name="grade_api_v2"),
]
