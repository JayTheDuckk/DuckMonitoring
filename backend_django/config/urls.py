from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

def root_view(request):
    """Root API endpoint with basic info"""
    return JsonResponse({
        'name': 'Duck Monitoring API',
        'version': '2.0',
        'status': 'running',
        'endpoints': {
            'admin': '/admin/',
            'auth': '/api/auth/',
            'inventory': '/api/inventory/',
            'monitoring': '/api/monitoring/',
            'agents': '/api/agents/',
            'alerts': '/api/alerts/',
        },
        'frontend': 'http://localhost:3000',
        'docs': 'API endpoints are available at /api/*'
    })

urlpatterns = [
    path('', root_view, name='root'),
    path('admin/', admin.site.urls),
    
    # Auth endpoints
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', include('accounts.urls')),
    
    # Application endpoints
    path('api/inventory/', include('inventory.urls')),
    path('api/monitoring/', include('monitoring.urls')),
    path('api/agents/', include('monitoring.agent_urls')),
    path('api/alerts/', include('alerts.urls')),
    path('api/discovery/', include('discovery.urls')),
    path('api/', include('topology.urls')), # Includes /api/topology/graph
]
