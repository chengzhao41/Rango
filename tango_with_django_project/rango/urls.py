__author__ = 'Cheng'

from django.conf.urls import patterns, url
import views

urlpatterns = patterns('',
                       url(r'^$', views.index, name='index'),
                       url(r'^about/', views.about, name='about'),
)


