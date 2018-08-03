from django.conf.urls import url
from django.urls import path
from db import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path('category/<str:category>/', views.CategoryView.as_view()),
    path('tags/<str:tags>/', views.TagView.as_view()),
    path('id/<uuid:id>/', views.ObjectView.as_view()),
    path('name/<str:name>/', views.NameView.as_view()),
    path('tools/add_object_from_thingiverse/',views.AddObjectFromThingiverse.as_view())
]
