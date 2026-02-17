from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, RegisterSerializer

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    """
    Public endpoint to register a new user.
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint for the current logged-in user to view or update their profile.
    """
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def get_object(self):
        return self.request.user

class UserViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for managing all users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser,)

from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ['action', 'resource_type', 'user__username']

    @action(detail=False, methods=['get'])
    def actions(self, request):
        actions = AuditLog.objects.values_list('action', flat=True).distinct()
        return Response(list(actions))

    @action(detail=False, methods=['get'], url_path='resource-types')
    def resource_types(self, request):
        types = AuditLog.objects.values_list('resource_type', flat=True).distinct()
        return Response(list(types))

    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'

        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'User', 'Action', 'Resource Type', 'Resource ID', 'IP Address', 'Details'])

        logs = self.filter_queryset(self.get_queryset())
        for log in logs:
            writer.writerow([
                log.timestamp,
                log.user.username if log.user else 'Unknown',
                log.action,
                log.resource_type,
                log.resource_id,
                log.ip_address,
                log.details
            ])

        return response
