from django.db import models
from django.contrib.auth.models import User


class Note(models.Model):
    """Main note model"""
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default='')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title


class SharedAccess(models.Model):
    """Collaboration/sharing model"""
    ROLE_CHOICES = [
        ('viewer', 'Viewer'),
        ('editor', 'Editor'),
    ]
    
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='shared_access')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_notes')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='viewer')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['note', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.note.title} ({self.role})"


class NoteVersion(models.Model):
    """Version history for notes"""
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='versions')
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.note.title} - v{self.version_number}"


class ActivityLog(models.Model):
    """Audit trail for notes"""
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('shared', 'Shared'),
        ('unshared', 'Unshared'),
        ('restored', 'Restored'),
    ]
    
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.note.title} by {self.user}"
