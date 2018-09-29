from django.conf.urls import url, include
from django.urls import path
from thingiverse import views
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'thingiverse'

urlpatterns = [
path('get_api_key/',views.ThingiverseAPIKeyRequestView.as_view()),
path('add_object/',views.AddObjectFromThingiverse.as_view(), name='import_from_thingi_url'),

]
