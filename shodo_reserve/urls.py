"""
URL configuration for shodo_reserve project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from booking.auth_views import (
    CustomLoginView,
    CustomPasswordResetView,
    CustomPasswordResetConfirmView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("booking.urls")),
    path("accounts/login/", CustomLoginView.as_view(), name='login'),
    path("accounts/password_reset/", CustomPasswordResetView.as_view(), name='password_reset'),
    path("accounts/reset/<uidb64>/<token>/", CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path("accounts/", include("django.contrib.auth.urls")),
]
