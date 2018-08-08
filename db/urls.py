from django.conf.urls import url, include
from django.urls import path
from db import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path('query/category/<str:category>/', views.CategoryView.as_view()),
    path('query/tag/<str:tags>/', views.TagView.as_view()),
    path('query/id/<uuid:id>/', views.ObjectView.as_view()),
    path('query/name/<str:name>/', views.NameView.as_view()),
    path('list/object', views.ListAllObjectsView.as_view()),
    path('list/category', views.ListAllCategoriesView.as_view()),
    path('list/tag', views.ListAllTagsView.as_view()),
    path('tools/add_object_from_thingiverse/',views.AddObjectFromThingiverse.as_view()),
    path('rest-auth/', include('rest_auth.urls')),
    path('test',views.UserTest.as_view()),
]
