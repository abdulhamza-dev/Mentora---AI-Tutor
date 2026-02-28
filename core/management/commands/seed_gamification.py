from django.core.management.base import BaseCommand
from core.models import Level, Achievement, Subject, Quiz

class Command(BaseCommand):
    help = 'Seed initial data for the gamification system'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding levels...')
        levels_data = [
            (1, 'Novice Learner', 0),
            (2, 'Curious Mind', 100),
            (3, 'Knowledge Seeker', 200),
            (4, 'Scholar in Training', 300),
            (5, 'Smart Explorer', 400),
            (6, 'Master Student', 500),
            (7, 'Elite Thinker', 600),
            (8, 'Grand Polymath', 700),
            (9, 'Ultra Intelligence', 800),
            (10, 'Mentora Sage', 900),
        ]
        for num, title, xp in levels_data:
            Level.objects.get_or_create(
                number=num, 
                defaults={'title': title, 'xp_threshold': xp}
            )

        self.stdout.write('Seeding achievements...')
        achievements_data = [
            ('Star Gazer', 'Unlock your first astronomy lesson', 'star', 10, 0, 0),
            ('Mind Explorer', 'Complete your first psychology quiz', 'brain', 0, 0, 1),
            ('7-Day Streak', 'Keep learning for a full week!', 'flame', 0, 7, 0),
            ('Knowledge Master', 'Earn 1000 total XP', 'trophy', 1000, 0, 0),
        ]
        for name, desc, icon, xp_req, streak_req, quiz_req in achievements_data:
            Achievement.objects.get_or_create(
                name=name, 
                defaults={
                    'description': desc, 
                    'icon': icon, 
                    'xp_required': xp_req,
                    'streak_required': streak_req,
                    'quiz_count_required': quiz_req
                }
            )

        self.stdout.write('Seeding sample subjects and quizzes...')
        # Create subjects first
        subjects = ['Astronomy', 'Psychology', 'World History', 'Philosophy']
        for s_name in subjects:
            Subject.objects.get_or_create(name=s_name)

        quizzes_data = [
            ('Astronomy', 'The Solar System Basics', 50),
            ('Psychology', 'Understanding Human Emotions', 50),
            ('World History', 'Ancient Civilizations', 50),
        ]
        for s_name, title, xp in quizzes_data:
            subj = Subject.objects.get(name=s_name)
            Quiz.objects.get_or_create(
                subject=subj, 
                title=title, 
                defaults={'xp_reward': xp}
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded gamification data!'))
