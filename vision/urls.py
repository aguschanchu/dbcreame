from django.conf.urls import url, include
from django.urls import path
from vision import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'vision'

urlpatterns = []

urlpatterns += [
path('', views.VisionAPIPostURL.as_view(),name='post_url'),
path('status/<uuid:id>/',views.VisionAPIStatusURL.as_view(),name='status_url'),
path('retrieve/<uuid:id>/',views.VisionAPIViewURL.as_view(),name='retrieve_url'),
]
