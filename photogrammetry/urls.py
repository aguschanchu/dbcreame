from django.conf.urls import url, include
from django.urls import path
from photogrammetry import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'photogrammetry'

urlpatterns = []

urlpatterns += [
path('create/', views.CreateJobView.as_view()),
path('add_image/', views.AddImageToJob.as_view()),
path('status/<uuid:id>/', views.ViewJob.as_view()),
]
