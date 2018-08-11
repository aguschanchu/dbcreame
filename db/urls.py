from django.conf.urls import url, include
from django.urls import path
from db import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = []

#Query View
urlpatterns += [
path('query/category/<str:category>/', views.CategoryView.as_view()),
path('query/tag/<str:tags>/', views.TagView.as_view()),
path('query/id/<uuid:id>/', views.ObjectView.as_view()),
path('query/name/<str:name>/', views.NameView.as_view())
]
#List view
urlpatterns += [
path('list/object', views.ListAllObjectsView.as_view()),
path('list/category', views.ListAllCategoriesView.as_view()),
path('list/tag', views.ListAllTagsView.as_view())
]
#Operations
urlpatterns += [
path('update/like/<uuid:id>/',views.ToggleLike.as_view())
]
#External tools
urlpatterns += [
path('tools/add_object_from_thingiverse/',views.AddObjectFromThingiverse.as_view())
]
#Auth
urlpatterns += [
path('accounts/', include('rest_auth.urls')),
url(r'^accounts/registration/', include('rest_auth.registration.urls')),
url(r'^accounts/facebook/$', views.FacebookLogin.as_view(), name='fb_login'),
url(r'^accounts/google/login/callback/$', views.GoogleLogin.as_view(), name='google_callback'),
]
