from django.urls import path

from cloudinary_app import views

urlpatterns = [
    path("", views.image_upload_view, name="image_upload_view"),
    path('success/', views.success_view, name='success'),
]