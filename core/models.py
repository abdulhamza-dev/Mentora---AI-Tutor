from django.db import models
from django.contrib.auth.models import User

# Model to store user-specific details and subscription plan
class UserProfile(models.Model):
    PLAN_CHOICES = [
        ('FREE', 'Free Student'),
        ('BASIC', 'Pro Student'),
        ('ULTRA', 'Ultra Explorer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    interests = models.TextField(blank=True, help_text="What do you love learning about?")
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='FREE')
    questions_asked = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username}'s Profile - {self.plan}"

# Model to store AI-teacher conversations
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    topic = models.CharField(max_length=255)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.topic} - {self.created_at}"
