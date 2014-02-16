from django.conf.urls import patterns, url
from django.http import HttpResponse

urlpatterns = patterns(
    '',
    url(r'^export1\.(?P<format>\w+)$', lambda request: HttpResponse("THIS"), name='this'),
    url(r'^export2(\.(?P<format>\w+))?$', lambda request: HttpResponse("THAT"), name='that'),
    url(r'^(?P<qq1>\d+)(?P<qq2>\d+)?$', lambda request: HttpResponse("QQ"), name='qq'),
    url(r'^(?P<q>\.(?P<qq1>\d+)\.(?P<qq2>\d+))$', lambda request: HttpResponse("Q"), name='q'),
)
