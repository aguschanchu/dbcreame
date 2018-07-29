from django.conf.urls import url
from db import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    url(r'^category/(?P<category>[\w.@+-]+)/$', views.CategoryView.as_view()),
    url(r'^object/(?P<id>[\w.@+-]+)/$', views.ObjectView.as_view()),
]
