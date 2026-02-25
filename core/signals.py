from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from .models import XPTransaction, UserProfile, Level, Badge, UserBadge, LoginHistory

@receiver(user_logged_in)
def track_login(sender, request, user, **kwargs):
    """ Record login activity in LoginHistory """
    ip = request.META.get('REMOTE_ADDR')
    ua = request.META.get('HTTP_USER_AGENT')
    LoginHistory.objects.create(user=user, ip_address=ip, user_agent=ua)

@receiver(post_save, sender=XPTransaction)
def handle_xp_gain(sender, instance, created, **kwargs):
    """
    When XP is added, update the user profile total XP,
    check for level up, and check for badge milestones.
    """
    if created:
        profile = instance.user.profile
        profile.total_xp += instance.amount
        
        # Check for Level Up
        # Find the highest level where xp_threshold <= total_xp
        new_level = Level.objects.filter(xp_threshold__lte=profile.total_xp).order_by('-number').first()
        if new_level and (not profile.current_level or new_level.number > profile.current_level.number):
            profile.current_level = new_level
        
        profile.save()
        
        # Check for Badge Rewards (XP based)
        check_badge_milestones(instance.user, 'XP', profile.total_xp)

def check_badge_milestones(user, requirement_type, current_value):
    """
    Check if the user has reached any new badge milestones.
    """
    eligible_badges = Badge.objects.filter(
        requirement_type=requirement_type,
        requirement_value__lte=current_value
    ).exclude(id__in=user.badges.values_list('badge_id', flat=True))
    
    for badge in eligible_badges:
        UserBadge.objects.get_or_create(user=user, badge=badge)

@receiver(post_save, sender=UserProfile)
def handle_streak_update(sender, instance, **kwargs):
    """
    Check for streak-based badges when the profile is updated.
    """
    check_badge_milestones(instance.user, 'STREAK', instance.current_streak)
