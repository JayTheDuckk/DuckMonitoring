from django.urls import path
from .agent_views import AgentRegisterView, AgentSubmitView

urlpatterns = [
    path('register', AgentRegisterView.as_view(), name='agent-register-noslash'),
    path('submit', AgentSubmitView.as_view(), name='agent-submit-noslash'),
    path('register/', AgentRegisterView.as_view(), name='agent-register'),
    path('submit/', AgentSubmitView.as_view(), name='agent-submit'),
]
