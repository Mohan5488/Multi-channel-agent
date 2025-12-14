from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ServiceCredential(models.Model):
    """
    Generic storage for user OAuth credentials / tokens for many services.
    One row per (user, service_name).
    """
    SERVICE_CHOICES = [
        ("gmail", "Gmail"),
        ("google_calendar", "Google Calendar"),
        ("custom_api", "Custom API"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="service_credentials")
    service = models.CharField(max_length=64, choices=SERVICE_CHOICES)

    data = models.JSONField(default=dict) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "service")
        indexes = [
            models.Index(fields=["user", "service"]),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.service}"
