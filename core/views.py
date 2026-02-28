import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from freeflow_llm import FreeFlowClient
from dotenv import load_dotenv
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Subject, Conversation, UserProfile, XPTransaction, Level, Achievement, UserAchievement, Quiz, UserQuizAttempt, UserAnswer
from .services import award_xp
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.sessions.models import Session
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

# Initialize FreeFlow Client
def get_freeflow_client():
    from django.conf import settings
    env_path = os.path.join(settings.BASE_DIR, '.env')
    load_dotenv(env_path)
    return FreeFlowClient()

def teacher_view(request, subject="General Learning"):
    """Render the AI Teacher interface."""
    current_day = 1
    subject_obj, _ = Subject.objects.get_or_create(name=subject)
    
    return render(request, 'core/teacher.html', {
        'subject': subject_obj.name,
        'current_day': current_day
    })

def landing_view(request):
    """Render the new landing page."""
    return render(request, 'core/index.html')

def login_view(request):
    """Render the login page and handle authentication."""
    if request.method == 'POST':
        email = request.POST.get('username')  # We use email as username
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('account')
        else:
            return render(request, 'core/login.html', {'error': 'Invalid credentials'})
    return render(request, 'core/login.html')

def signup_view(request):
    """Render the signup page and handle user registration."""
    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            return render(request, 'core/signup.html', {'error': 'Passwords do not match'})
            
        if User.objects.filter(username=email).exists():
            return render(request, 'core/signup.html', {'error': 'Email already registered'})
            
        user = User.objects.create_user(username=email, email=email, password=password)
        login(request, user)
        return redirect('account')
    return render(request, 'core/signup.html')

def logout_view(request):
    """Handle user logout."""
    logout(request)
    return redirect('teacher_interface')

def chat_history_view(request):
    """API endpoint to get chat history."""
    topic = request.GET.get('topic', 'General Learning')
    
    if not request.user.is_authenticated:
        return JsonResponse({"history": []})

    history = Conversation.objects.filter(user=request.user, topic=topic)
        
    data = [
        {
            "id": h.id,
            "question": h.question, 
            "answer": h.answer, 
            "topic": h.topic,
            "day": None,
            "timestamp": h.created_at.isoformat()
        }
        for h in history
    ]
    return JsonResponse({"history": data})

def subject_days_view(request):
    """Return status for all 14 days of the requested subject."""
    subject = request.GET.get('subject', 'General Learning')
    subject_obj, _ = Subject.objects.get_or_create(name=subject)
    current_day = 1 # Simplified for now
    
    days = []
    # Using 14 days as a standard for now
    for d in range(1, 15):
        status = "locked"
        if d < current_day:
            status = "completed"
        elif d == current_day:
            status = "in_progress"
        
        days.append({
            "day": d,
            "status": status,
            "label": f"Day {d}"
        })
    return JsonResponse({"days": days})

@login_required
def delete_chat_view(request, chat_id):
    """API endpoint to delete a specific conversation."""
    try:
        chat = Conversation.objects.get(id=chat_id, user=request.user)
        chat.delete()
        return JsonResponse({"status": "success"})
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "Chat not found"}, status=404)

class AccountPageView(LoginRequiredMixin, TemplateView):
    template_name = 'core/account.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        
        # Gamification Data
        achievements = self.request.user.achievements.all().select_related('achievement')
        next_level_number = profile.current_level.number + 1 if profile.current_level else 2
        next_level = Level.objects.filter(number=next_level_number).first()
        
        # XP Progress (Targeting 100 XP per level)
        current_lvl_num = profile.current_level.number if profile.current_level else 0
        xp_in_level = profile.total_xp % 100
        xp_progress = xp_in_level # Since 100 is the threshold
        xp_needed_to_next = 100 - xp_in_level

        # Achievements Fetch
        all_achievements = Achievement.objects.all()
        user_ach_ids = set(achievements.values_list('achievement_id', flat=True))
        
        achievements_with_status = []
        for ach in all_achievements:
            achievements_with_status.append({
                'achievement': ach,
                'is_earned': ach.id in user_ach_ids
            })

        # Activity Feed
        activity_items = []
        
        # 1. Logins
        for login_act in self.request.user.login_history.all()[:5]:
            activity_items.append({
                'type': 'login',
                'title': 'Login',
                'sub': f'{timezone.localtime(login_act.timestamp).strftime("%b %d, %H:%M")}',
                'timestamp': login_act.timestamp,
                'xp': '—'
            })
        
        # 2. Quiz Attempts
        quiz_attempts = UserQuizAttempt.objects.filter(
            user=self.request.user, 
            completed_at__isnull=False
        ).order_by('-completed_at')[:5]
        
        for qa in quiz_attempts:
            try:
                dt_str = timezone.localtime(qa.completed_at).strftime("%b %d")
                activity_items.append({
                    'type': 'quiz',
                    'title': f'Completed Quiz — {qa.quiz.title}',
                    'sub': f'{qa.quiz.subject.name} · {dt_str}',
                    'timestamp': qa.completed_at,
                    'xp': f'+{qa.quiz.xp_reward} XP'
                })
            except Exception:
                continue
        
        # 3. XP Transactions
        xp_trans = XPTransaction.objects.filter(user=self.request.user).exclude(reason__icontains="Quiz").order_by('-timestamp')[:5]
        for xt in xp_trans:
            activity_items.append({
                'type': 'achievement',
                'title': xt.reason,
                'sub': f'{timezone.localtime(xt.timestamp).strftime("%b %d")}',
                'timestamp': xt.timestamp,
                'xp': f'+{xt.amount} XP'
            })
        
        activity_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        context.update({
            'profile': profile,
            'xp_progress': xp_progress,
            'xp_needed_to_next': xp_needed_to_next,
            'next_level': next_level,
            'badges_with_status': achievements_with_status[:8],
            'activity_items': activity_items[:8],
            'completed_quizzes': profile.quizzes_completed,
            'password_form': PasswordChangeForm(self.request.user)
        })
        return context

    def post(self, request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        action = request.POST.get('action')
        
        if action == 'update_profile':
            new_username = request.POST.get('username')
            new_full_name = request.POST.get('name', '')
            
            if new_username:
                if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
                    messages.error(request, "This username is already taken.")
                else:
                    request.user.username = new_username
            
            # Update User full name fields (first/last name)
            if new_full_name:
                if ' ' in new_full_name:
                    first, last = new_full_name.split(' ', 1)
                    request.user.first_name = first
                    request.user.last_name = last
                else:
                    request.user.first_name = new_full_name
                    request.user.last_name = ''
            
            request.user.save()
            
            profile.full_name = new_full_name
            profile.interests = request.POST.get('interests', '')
            profile.skill_level = request.POST.get('skill_level', 'BEGINNER')
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            messages.success(request, "Profile updated successfully!")
            
        elif action == 'change_password':
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully!")
            else:
                # Get the first error message
                error_msg = next(iter(form.errors.values()))[0]
                messages.error(request, f"Password update failed: {error_msg}")
                    
        elif action == 'toggle_2fa':
            profile.is_2fa_enabled = not profile.is_2fa_enabled
            profile.save()
            status_text = "enabled" if profile.is_2fa_enabled else "disabled"
            messages.success(request, f"2FA has been {status_text}!")
            
        elif action == 'logout_all':
            sessions = Session.objects.filter(expire_date__gte=timezone.now())
            for session in sessions:
                if str(request.user.pk) == session.get_decoded().get('_auth_user_id'):
                    session.delete()
            messages.success(request, "You have been logged out from all devices.")
            return redirect('login')

        elif action == 'delete_account':
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Your account has been deleted.")
            return redirect('landing_page')
            
        return redirect('account')

def pricing_view(request):
    """Render the pricing plans page."""
    return render(request, 'core/pricing.html')

def health_check(request):
    """Simple health check endpoint."""
    return JsonResponse({"status": "Server running"})

class AskAIView(APIView):
    """
    POST endpoint to ask the AI Teacher a question.
    Expects JSON: {"question": "...", "topic": "..."}
    """
    def post(self, request):
        question = request.data.get('question')
        topic = request.data.get('topic')

        if not question or not topic:
            return Response(
                {"error": "Both 'question' and 'topic' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle Authentication and Guest Limits
        if not request.user.is_authenticated:
            # Guest Limit Check (3 questions per session)
            guest_count = request.session.get('guest_question_count', 0)
            if guest_count >= 3:
                return Response(
                    {"error": "Guest limit reached", "limit_reached": True},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Use/Create a shadow user for guests or just track in session
            user, _ = User.objects.get_or_create(username='guest_student')
            request.session['guest_question_count'] = guest_count + 1
        else:
            user = request.user
            profile, _ = UserProfile.objects.get_or_create(user=user)
            
            # Limit for Free Tier (Increased to 100 for testing)
            if profile.plan == 'FREE' and profile.questions_asked >= 100:
                return Response(
                    {"error": "You've used all your free lessons! Please upgrade your plan to keep learning.", "limit_reached": True, "is_logged_in": True},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            profile.questions_asked += 1
            profile.save()

        try:
            # Call FreeFlow LLM API
            client = get_freeflow_client()
            
            # Simplified Day Tracking
            current_day = 1
            if request.user.is_authenticated:
                # We could track subject progress here if needed, 
                # but for now we follow the simple 100 XP leveling.
                pass
            
            # Fetch recent conversation history for memory
            history_objs = Conversation.objects.filter(
                user=user, 
                topic=topic
            ).order_by('-created_at')[:5]

            # Simplified curriculum context
            curriculum_context = f"Topic: {topic}. Target Level: 100 XP milestones."

            system_instr = (
                f"You are Mentora, a friendly AI Tutor for {topic}. "
                "Sound like a caring teacher. Keep responses concise (under 100 words). "
                "Use emojis! 🌈✨"
            )
            
            messages = [{"role": "system", "content": system_instr}]
            for chat in reversed(history_objs):
                messages.append({"role": "user", "content": chat.question})
                messages.append({"role": "assistant", "content": chat.answer})
            messages.append({"role": "user", "content": question})

            response = client.chat(messages=messages, timeout=15.0)
            answer = response.content

            # Save conversation
            Conversation.objects.create(
                user=user,
                topic=topic,
                question=question,
                answer=answer
            )

            return Response({"answer": answer}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardStatsView(APIView):
    """
    GET: Fetch personalized gamification stats for the student dashboard.
    Also handles daily streak updates and awards daily login XP.
    """
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        today = timezone.now().date()
        
        # Streak Update Logic
        if profile.last_login_date:
            if profile.last_login_date == today:
                pass
            elif profile.last_login_date == today - timedelta(days=1):
                profile.current_streak += 1
                if profile.current_streak > profile.max_streak:
                    profile.max_streak = profile.current_streak
                
                # Bonus XP for 7-day streak
                if profile.current_streak == 7:
                    award_xp(request.user, 100, "7-Day Streak Bonus!")
            else:
                profile.current_streak = 1
        else:
            profile.current_streak = 1
            
        profile.last_login_date = today
        profile.save()
        
        from .serializers import DashboardStatsSerializer
        serializer = DashboardStatsSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CompleteQuizView(APIView):
    """
    POST: Mark a quiz as completed and reward the student with XP.
    Expects JSON: {"quiz_id": 123, "score": 85, "time_taken": 120}
    """
    def post(self, request):
        quiz_id = request.data.get('quiz_id')
        score = request.data.get('score', 0)
        time_taken = request.data.get('time_taken', 0)
        
        try:
            quiz = Quiz.objects.get(id=quiz_id)
            
            # Record Attempt
            attempt = UserQuizAttempt.objects.create(
                user=request.user,
                quiz=quiz,
                score=score,
                total_questions=quiz.questions.count(),
                time_taken_seconds=time_taken,
                completed_at=timezone.now()
            )
            
            # Update Profile Count
            profile = request.user.profile
            profile.quizzes_completed += 1
            profile.save()
            
            # Award XP using service (+50 XP as per requirement)
            award_xp(request.user, quiz.xp_reward, f"Quiz Completed: {quiz.title}")
            
            return Response({
                "status": "success", 
                "xp_earned": quiz.xp_reward,
                "message": f"Fantastic! You earned {quiz.xp_reward} XP!"
            }, status=status.HTTP_200_OK)
                
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)
