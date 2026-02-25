from django.core.management.base import BaseCommand
from core.models import Level, Badge, Quiz, SurpriseChallenge

class Command(BaseCommand):
    help = 'Seed initial data for the gamification system'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding levels...')
        levels_data = [
            (1, 'Novice Learner', 0),
            (2, 'Curious Mind', 500),
            (3, 'Knowledge Seeker', 1200),
            (4, 'Scholar in Training', 2000),
            (5, 'Smart Explorer', 3000),
            (6, 'Master Student', 4200),
            (7, 'Elite Thinker', 5600),
            (8, 'Grand Polymath', 7200),
            (9, 'Ultra Intelligence', 9000),
            (10, 'Mentora Sage', 11000),
        ]
        for num, title, xp in levels_data:
            Level.objects.get_or_create(number=num, defaults={'title': title, 'xp_threshold': xp})

        self.stdout.write('Seeding badges...')
        badges_data = [
            ('Star Gazer', 'Unlock your first astronomy lesson', 'star', 'XP', 100),
            ('Mind Explorer', 'Complete your first psychology quiz', 'brain', 'QUIZ', 1),
            ('7-Day Streak', 'Keep learning for a full week!', 'flame', 'STREAK', 7),
            ('Space Pioneer', 'Reach Level 5 as an explorer', 'rocket', 'XP', 3000),
            ('Knowledge Master', 'Earn 10,000 total XP', 'trophy', 'XP', 10000),
        ]
        for name, desc, icon, req_type, req_val in badges_data:
            Badge.objects.get_or_create(
                name=name, 
                defaults={
                    'description': desc, 
                    'icon_name': icon, 
                    'requirement_type': req_type, 
                    'requirement_value': req_val
                }
            )

        self.stdout.write('Seeding sample quizzes...')
        quizzes_data = [
            ('Astronomy', 1, 'The Solar System Basics', 200),
            ('Psychology', 1, 'Understanding Human Emotions', 200),
            ('World History', 1, 'The Rise of Ancient Civilizations', 200),
        ]
        for subject, day, title, xp in quizzes_data:
            Quiz.objects.get_or_create(
                subject=subject, 
                day=day, 
                defaults={'title': title, 'xp_reward': xp}
            )

        self.stdout.write('Seeding surprise challenges...')
        challenges_data = [
            ('Quick Thinker', 'Ask 5 questions in 5 minutes', 150),
            ('Night Owl', 'Learn after 10 PM for extra XP', 200),
        ]
        for title, desc, xp in challenges_data:
            SurpriseChallenge.objects.get_or_create(
                title=title, 
                defaults={'description': desc, 'xp_reward': xp}
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded gamification data!'))
