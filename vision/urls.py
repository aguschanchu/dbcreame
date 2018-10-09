from django.conf.urls import url, include
from django.urls import path
from vision import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'vision'

urlpatterns = []

urlpatterns += [
path('create/', views.VisionAPIPostURL.as_view()),
path('retrieve/<uuid:id>/',views.VisionAPIViewURL.as_view()),
]
