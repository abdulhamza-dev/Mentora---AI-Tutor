from .models import XPTransaction, Level, Achievement, UserAchievement, UserProfile
from django.db.models import F

def award_xp(user, amount, reason):
    """
    Centralized function to award XP to a user.
    Records transaction, updates profile, checks for level up and achievements.
    """
    profile = user.profile
    
    # 1. Record Transaction
    XPTransaction.objects.create(user=user, amount=amount, reason=reason)
    
    # 2. Update Total XP
    profile.total_xp += amount
    
    # 3. Check for Level Up
    # level = total_xp // 100 as per requirement
    new_level_number = profile.total_xp // 100
    if new_level_number == 0: new_level_number = 1
    
    current_level_number = profile.current_level.number if profile.current_level else 0
    
    if new_level_number > current_level_number:
        # Update current level and title
        level_obj, created = Level.objects.get_or_create(
            number=new_level_number,
            defaults={
                'title': get_level_title(new_level_number),
                'xp_threshold': new_level_number * 100
            }
        )
        profile.current_level = level_obj
    
    profile.save()
    
    # 4. Check for Achievement Milestones
    check_achievements(user)

def get_level_title(level_number):
    """ Mapping level numbers to dynamic titles """
    if level_number <= 2: return "Smart Explorer"
    if level_number <= 5: return "Knowledge Seeker"
    if level_number <= 10: return "Mind Master"
    return "AI Scholar"

def check_achievements(user):
    """
    Check if user has met requirements for any new achievements.
    """
    profile = user.profile
    
    # Get achievements not yet earned
    earned_ids = user.achievements.values_list('achievement_id', flat=True)
    potential_achievements = Achievement.objects.exclude(id__in=earned_ids)
    
    for ach in potential_achievements:
        meet_xp = (ach.xp_required == 0 or profile.total_xp >= ach.xp_required)
        meet_streak = (ach.streak_required == 0 or profile.current_streak >= ach.streak_required)
        meet_quiz = (ach.quiz_count_required == 0 or profile.quizzes_completed >= ach.quiz_count_required)
        
        if meet_xp and meet_streak and meet_quiz:
            UserAchievement.objects.get_or_create(user=user, achievement=ach)
