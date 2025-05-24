"""
URL configuration for ecommerce_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.views import (
    CartViewSet,
    CreatePaymentAPIView,
    OrderViewSet,
    PaymentCancelAPIView,
    PaymentSuccessAPIView,
    ProductViewSet,
    UserViewSet,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("pay/<uuid:order_id>/", CreatePaymentAPIView.as_view(), name="create-payment"),
    path("paypal/success/", PaymentSuccessAPIView.as_view(), name="paypal-success"),
    path("paypal/cancel/", PaymentCancelAPIView.as_view(), name="paypal-cancel"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("silk/", include("silk.urls", namespace="silk")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]


routers = DefaultRouter()
routers.register("users", UserViewSet)
routers.register("products", ProductViewSet)
routers.register("orders", OrderViewSet)
routers.register("carts", CartViewSet)
urlpatterns += routers.urls
