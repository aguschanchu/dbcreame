from django.conf.urls import url
from django.urls import path
from db import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    url(r'^category/(?P<category>[\w.@+-]+)/$', views.CategoryView.as_view()),
    path('view/<uuid:id>/', views.ObjectView.as_view()),
]
