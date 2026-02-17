import logging
import json
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import Alert, AlertRule, NotificationChannel, AlertHistory, MaintenanceWindow

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_notification(channel, subject, message):
        """
        Dispatches notification based on channel type.
        """
        try:
            if channel.channel_type == 'email':
                NotificationService._send_email(channel, subject, message)
            elif channel.channel_type == 'slack':
                NotificationService._send_slack(channel, subject, message)
            elif channel.channel_type == 'discord':
                NotificationService._send_discord(channel, subject, message)
            elif channel.channel_type == 'webhook':
                NotificationService._send_webhook(channel, subject, message)
        except Exception as e:
            logger.error(f"Failed to send notification to {channel.name}: {e}")

    @staticmethod
    def _send_email(channel, subject, message):
        config = channel.config
        recipient = config.get('email') or config.get('to')
        if not recipient:
            logger.warning(f"No email recipient for channel {channel.name}")
            return
            
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )

    @staticmethod
    def _send_slack(channel, subject, message):
        config = channel.config
        webhook_url = config.get('webhook_url') or config.get('url')
        if not webhook_url:
            return
            
        payload = {
            "text": f"*{subject}*\n{message}"
        }
        requests.post(webhook_url, json=payload, timeout=5)

    @staticmethod
    def _send_discord(channel, subject, message):
        config = channel.config
        webhook_url = config.get('webhook_url') or config.get('url')
        if not webhook_url:
            return

        payload = {
            "content": f"**{subject}**\n{message}"
        }
        requests.post(webhook_url, json=payload, timeout=5)
        
    @staticmethod
    def _send_webhook(channel, subject, message):
        config = channel.config
        url = config.get('url')
        if not url:
            return
            
        payload = {
            "subject": subject,
            "message": message,
            "timestamp": timezone.now().isoformat()
        }
        requests.post(url, json=payload, timeout=5)


class AlertService:
    @staticmethod
    def evaluate_alerts(host, check_result):
        """
        Evaluates filtering rules for a given host and check result.
        """
        # Check for maintenance windows
        active_maintenance = MaintenanceWindow.objects.filter(
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now(),
            suppress_alerts=True
        )
        
        # Check if host or its group is in maintenance
        in_maintenance = False
        for window in active_maintenance:
            if window.all_hosts:
                in_maintenance = True
                break
            if window.host and window.host == host:
                in_maintenance = True
                break
            if window.host_group and window.host_group == host.group:
                in_maintenance = True
                break
                
        if in_maintenance:
            return # Suppress alerts
            
        # Fetch enabled rules for this host or its group
        # Direct host rules
        host_rules = AlertRule.objects.filter(host=host, enabled=True)
        # Group rules
        group_rules = AlertRule.objects.filter(host_group=host.group, enabled=True) if host.group else []
        
        # Combine
        rules = list(host_rules) + list(group_rules)
        
        for rule in rules:
            AlertService._evaluate_rule(rule, host, check_result)

    @staticmethod
    def _evaluate_rule(rule, host, check_result):
        """
        Evaluates a single rule against the check result.
        """
        condition = rule.condition
        # Schema: {"field": "status", "operator": "equals", "value": "critical"}
        
        field = condition.get('field')
        operator = condition.get('operator')
        target_value = condition.get('value')
        
        # Get actual value from result
        actual_value = None
        if field == 'status':
            actual_value = check_result.status
        elif field == 'response_time':
            actual_value = check_result.response_time
        # Add more fields as needed
        
        if actual_value is None:
            return
            
        is_triggered = False
        
        # Compare
        if operator == 'equals' or operator == '==':
             is_triggered = str(actual_value) == str(target_value)
        elif operator == 'not_equals' or operator == '!=':
             is_triggered = str(actual_value) != str(target_value)
        elif operator == 'gt' or operator == '>':
             try:
                 is_triggered = float(actual_value) > float(target_value)
             except: pass
        elif operator == 'lt' or operator == '<':
             try:
                 is_triggered = float(actual_value) < float(target_value)
             except: pass
             
        # Find existing active alert for this rule/host
        active_alert = Alert.objects.filter(
            rule=rule,
            host=host,
            status__ne='resolved' # Only firing or ack
        ).first() # Django filter ne? No, exclude resolved
        
        active_alert = Alert.objects.filter(
            rule=rule,
            host=host
        ).exclude(status='resolved').first()
        
        if is_triggered:
            if not active_alert:
                # Create new alert
                alert = Alert.objects.create(
                    rule=rule,
                    host=host,
                    service_check=check_result.service_check,
                    title=f"Alert: {rule.name} on {host.display_name or host.hostname}",
                    message=f"Condition met: {field} {operator} {target_value}. Actual: {actual_value}",
                    severity=rule.severity,
                    status='firing'
                )
                AlertService._notify(alert, "Triggered")
            else:
                # Update existing? Maybe update last seen?
                pass
        else:
            # Condition NOT met. If there is an active alert, Resolve it
            if active_alert and active_alert.status != 'resolved':
                active_alert.status = 'resolved'
                active_alert.resolved_at = timezone.now()
                active_alert.save()
                
                # Create history
                AlertHistory.objects.create(
                    alert=active_alert,
                    action='resolve',
                    previous_status='firing', # or ack
                    new_status='resolved',
                    details={'reason': 'Condition no longer met'}
                )
                
                AlertService._notify(active_alert, "Resolved")

    @staticmethod
    def _notify(alert, action):
        """
        Sends notifications for the alert.
        """
        channels = alert.rule.channels.all()
        if not channels.exists():
            return
            
        subject = f"[{alert.severity.upper()}] {action}: {alert.title}"
        message = f"""
        Alert: {alert.title}
        Status: {alert.status}
        Severity: {alert.severity}
        Host: {alert.host.hostname}
        Message: {alert.message}
        Triggered At: {alert.triggered_at}
        """
        
        for channel in channels:
            if channel.enabled:
                NotificationService.send_notification(channel, subject, message)
        
        # Update alert stats
        alert.last_notification_at = timezone.now()
        alert.notification_count += 1
        alert.save()
