from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from . import settings

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .health import health_check

schema_view = get_schema_view(
    openapi.Info(
        title="Multi_Shop API",
        default_version='v1',
        description="""
      Multi_Shop is a multi-vendor e-commerce platform API.

      Features:
      - User registration and authentication with token.
      - Vendor, Product, Order, and Customer management.
      """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="you@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[]
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Your app URLs
    path('account/',include('account.urls')),
    path('customer/',include('customer.urls')),
    path('vendor/',include('vendor.urls')),
    path('order/',include('order.urls')),
    path('dashboard/',include('dashboard.urls')),
    # Swagger UI
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # Redoc UI
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('website/', include('website.urls')),
    
    
    path('health/',health_check,name='health_check')
]

