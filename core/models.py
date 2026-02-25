from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Model to define levels and their XP requirements
class Level(models.Model):
    number = models.IntegerField(unique=True)
    title = models.CharField(max_length=100)
    xp_threshold = models.IntegerField(help_text="Total XP required to reach this level")

    def __str__(self):
        return f"Level {self.number}: {self.title} ({self.xp_threshold} XP)"

# Model to store user-specific details and gamification progress
class UserProfile(models.Model):
    PLAN_CHOICES = [
        ('FREE', 'Free Student'),
        ('BASIC', 'Pro Student'),
        ('ULTRA', 'Ultra Explorer'),
    ]
    
    SKILL_LEVEL_CHOICES = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    interests = models.TextField(blank=True, help_text="What do you love learning about?")
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVEL_CHOICES, default='BEGINNER')
    is_2fa_enabled = models.BooleanField(default=False)
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='FREE')
    questions_asked = models.IntegerField(default=0)
    
    # Gamification fields
    total_xp = models.IntegerField(default=0)
    current_level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile - Level {self.current_level.number if self.current_level else 1}"

# Model to track login activity
class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} logged in at {self.timestamp}"

# Model to track progress in specific subjects
class SubjectProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subject_progress')
    subject = models.CharField(max_length=100)
    current_day = models.IntegerField(default=1)
    day_question_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'subject')

    def __str__(self):
        return f"{self.user.username} - {self.subject} (Day {self.current_day})"

# Model to store AI-teacher conversations
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    topic = models.CharField(max_length=255)
    question = models.TextField()
    answer = models.TextField()
    day_number = models.IntegerField(default=1, help_text="The day number this conversation belongs to")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.topic} - {self.created_at}"

# Model to store available badges
class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon_name = models.CharField(max_length=50, help_text="Lucide icon name (e.g., 'star', 'rocket')")
    requirement_type = models.CharField(max_length=50, choices=[
        ('XP', 'XP Milestone'),
        ('STREAK', 'Streak Milestone'),
        ('QUIZ', 'Quiz Completion'),
    ])
    requirement_value = models.IntegerField()

    def __str__(self):
        return self.name

# Model to link users to earned badges
class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')

# Model to log XP transactions
class XPTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='xp_history')
    amount = models.IntegerField()
    reason = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} +{self.amount} XP ({self.reason})"

# Model for Quizzes
class Quiz(models.Model):
    subject = models.CharField(max_length=100)
    day = models.IntegerField()
    title = models.CharField(max_length=255)
    xp_reward = models.IntegerField(default=100)
    
    class Meta:
        unique_together = ('subject', 'day')

    def __str__(self):
        return f"{self.subject} - Day {self.day}: {self.title}"

# Model to track user quiz progress
class UserQuizProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_progress')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'quiz')

# Model for Surprise Challenges
class SurpriseChallenge(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    xp_reward = models.IntegerField(default=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
