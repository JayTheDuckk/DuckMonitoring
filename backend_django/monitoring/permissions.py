from rest_framework.permissions import BasePermission
from django.conf import settings


class AgentTokenPermission(BasePermission):
    """Require X-Agent-Token header when AGENT_API_TOKEN is configured."""

    def has_permission(self, request, view):
        token = settings.AGENT_API_TOKEN
        if not token:
            return True
        return request.headers.get('X-Agent-Token') == token
