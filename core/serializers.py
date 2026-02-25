from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Level, Badge, UserBadge, XPTransaction, Quiz, UserQuizProgress, SurpriseChallenge

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['number', 'title', 'xp_threshold']

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ['name', 'description', 'icon_name', 'requirement_type', 'requirement_value']

class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)
    class Meta:
        model = UserBadge
        fields = ['badge', 'earned_at']

class XPTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = XPTransaction
        fields = ['amount', 'reason', 'timestamp']

class SurpriseChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurpriseChallenge
        fields = ['title', 'description', 'xp_reward', 'is_active']

class DashboardStatsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    level = serializers.SerializerMethodField()
    badges_count = serializers.SerializerMethodField()
    recent_badges = serializers.SerializerMethodField()
    quizzes_remaining = serializers.SerializerMethodField()
    active_challenges = serializers.SerializerMethodField()
    xp_to_next_level = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'username', 'total_xp', 'level', 'current_streak', 'max_streak', 
            'badges_count', 'recent_badges', 'quizzes_remaining', 
            'active_challenges', 'xp_to_next_level', 'progress_percentage'
        ]

    def get_level(self, obj):
        if obj.current_level:
            return LevelSerializer(obj.current_level).data
        return {"number": 1, "title": "Beginner", "xp_threshold": 0}

    def get_badges_count(self, obj):
        return obj.user.badges.count()

    def get_recent_badges(self, obj):
        badges = obj.user.badges.all().order_by('-earned_at')[:4]
        return UserBadgeSerializer(badges, many=True).data

    def get_quizzes_remaining(self, obj):
        # Count quizzes not completed by user
        total_quizzes = Quiz.objects.count()
        completed_quizzes = UserQuizProgress.objects.filter(user=obj.user, completed=True).count()
        return max(0, total_quizzes - completed_quizzes)

    def get_active_challenges(self, obj):
        challenges = SurpriseChallenge.objects.filter(is_active=True)[:2]
        return SurpriseChallengeSerializer(challenges, many=True).data

    def get_xp_to_next_level(self, obj):
        current_level_num = obj.current_level.number if obj.current_level else 1
        next_level = Level.objects.filter(number=current_level_num + 1).first()
        if next_level:
            return next_level.xp_threshold
        return obj.total_xp # Max level reached

    def get_progress_percentage(self, obj):
        current_level_num = obj.current_level.number if obj.current_level else 1
        current_level_xp = obj.current_level.xp_threshold if obj.current_level else 0
        next_level = Level.objects.filter(number=current_level_num + 1).first()
        
        if not next_level:
            return 100
        
        total_needed = next_level.xp_threshold - current_level_xp
        earned = obj.total_xp - current_level_xp
        return min(100, max(0, int((earned / total_needed) * 100))) if total_needed > 0 else 0
