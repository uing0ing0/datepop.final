from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
import cloudinary_app 
from api import api

def test(request):
    return HttpResponse("Test successful!")


urlpatterns = [
    path('test/', test, name='test'),
    path("cloudinary_app/", include('cloudinary_app.urls')),
    path("admin/", admin.site.urls),
]
