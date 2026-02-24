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
from .models import Conversation, UserProfile, SubjectProgress

# Initialize FreeFlow Client
def get_freeflow_client():
    load_dotenv()
    return FreeFlowClient()

def teacher_view(request, subject="General Learning"):
    """Render the AI Teacher interface."""
    current_day = 1
    if request.user.is_authenticated:
        progress, _ = SubjectProgress.objects.get_or_create(user=request.user, subject=subject)
        current_day = progress.current_day
    
    return render(request, 'core/teacher.html', {
        'subject': subject,
        'current_day': current_day
    })

def landing_view(request):
    """Render the new landing page."""
    return render(request, 'core/index.html')

from django.contrib.auth import authenticate, login, logout

def login_view(request):
    """Render the login page and handle authentication."""
    if request.method == 'POST':
        email = request.POST.get('username')  # We use email as username
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('teacher_interface')
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
        return redirect('teacher_interface')
    return render(request, 'core/signup.html')

def logout_view(request):
    """Handle user logout."""
    logout(request)
    return redirect('teacher_interface')

def chat_history_view(request):
    """API endpoint to get chat history. Supports filtering by day for history mode."""
    day = request.GET.get('day')
    topic = request.GET.get('topic', 'General Learning')
    
    if request.user.is_authenticated:
        history = Conversation.objects.filter(user=request.user, topic=topic)
        if day:
            history = history.filter(day_number=day)
        else:
             # Default to current day
             progress, _ = SubjectProgress.objects.get_or_create(user=request.user, subject=topic)
             history = history.filter(day_number=progress.current_day)
    else:
        return JsonResponse({"history": []})
        
    data = [
        {
            "id": h.id,
            "question": h.question, 
            "answer": h.answer, 
            "topic": h.topic,
            "day": h.day_number,
            "timestamp": h.created_at.isoformat()
        }
        for h in history
    ]
    return JsonResponse({"history": data})

@login_required
def subject_days_view(request):
    """Return status for all 14 days of the requested subject."""
    subject = request.GET.get('subject', 'General Learning')
    progress, _ = SubjectProgress.objects.get_or_create(user=request.user, subject=subject)
    current_day = progress.current_day
    
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

@login_required
def account_view(request):
    """Render the user account/profile page and handle updates."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        interests = request.POST.get('interests')
        profile.interests = interests
        profile.save()
        return redirect('account')
    return render(request, 'core/account.html', {'profile': profile})

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
            
            # Generalized Day Tracking
            current_day = 1
            progress = None
            if request.user.is_authenticated:
                progress, _ = SubjectProgress.objects.get_or_create(user=user, subject=topic)
                current_day = progress.current_day
            
            # Fetch recent conversation history for memory (last 5 exchanges for CURRENT SUBJECT and DAY)
            # This prevents cross-subject memory leakage
            history_objs = Conversation.objects.filter(
                user=user, 
                topic=topic, 
                day_number=current_day
            ).order_by('-created_at')[:5]

            # Define the curriculum or special context based on the topic
            curriculum_context = f"CURRENT DAY: Day {current_day}\nINSTRUCTIONS:\n1. Focus on the current day's lesson.\n2. After 15 helpful exchanges, or if the student mastered the topic, suggest moving to 'Day {current_day + 1}' and include 'PROGRESS_UPDATE: NEXT_DAY' at the end."

            if "history" in topic.lower():
                chapters = [
                    "Origins of Humanity & Early Civilizations", "Ancient Mesopotamia & Egypt",
                    "Ancient Greece", "Ancient Rome", "The Middle Ages",
                    "Islamic Golden Age & The Mongols", "The Black Death & Growth of Towns"
                ]
                day_name = chapters[current_day - 1] if current_day <= len(chapters) else "Advanced History"
                curriculum_context += f"\nHISTORY CONTEXT: Focus strictly on {day_name}. DO NOT discuss Astronomy or Science unless asked."
            elif "astronomy" in topic.lower():
                chapters = ["Our Solar System", "Burning Stars", "The Milky Way", "Black Holes", "Space Exploration", "The Big Bang", "Galaxies Beyond"]
                day_name = chapters[current_day - 1] if current_day <= len(chapters) else "Astronomy"
                curriculum_context += f"\nASTRONOMY CONTEXT: Focus strictly on {day_name}."
            elif "biology" in topic.lower() or "science" in topic.lower():
                chapters = ["Building Blocks: Cells", "Plant Life", "Animal Kingdom", "Human Body", "Ecosystems", "Genetics", "Evolution"]
                day_name = chapters[current_day - 1] if current_day <= len(chapters) else "Science"
                curriculum_context += f"\nSCIENCE CONTEXT: Focus strictly on {day_name}. DO NOT discuss History or Philosophy."
            elif "philosophy" in topic.lower():
                chapters = ["Great Ideas", "Ethics", "Logic", "Ancient Thinkers", "The Nature of Mind", "Justice", "Existentialism"]
                day_name = chapters[current_day - 1] if current_day <= len(chapters) else "Philosophy"
                curriculum_context += f"\nPHILOSOPHY CONTEXT: Focus strictly on {day_name}. DO NOT talk about stars, galaxies, or science unless relevant to the philosophical concept."

            system_instr = (
                f"You are Antigravity, a friendly and intelligent {topic} Tutor for children aged 7–14. "
                "You are a real one-on-one personal tutor speaking through voice. "
                "IDENTITY & VOICE:\n"
                "1. Speak in a warm, gentle, friendly, and encouraging tone suitable for children.\n"
                "2. Use short sentences and natural pauses.\n"
                "3. Avoid robotic or formal language. Sound like a caring teacher speaking calmly to one child.\n"
                "4. Keep responses under 100 words unless telling a short story.\n"
                "5. Use encouraging phrases like 'That's a great question!' or 'You're thinking really well.'\n"
                "6. ALWAYS end with exactly ONE simple follow-up question.\n"
                "CONVERSATION BEHAVIOR:\n"
                "1. If the student pauses, wait patiently (keep responses flowing naturally).\n"
                "2. If audio is unclear, say: 'I didn’t catch that fully. Can you say it again?'\n"
                "3. Break complex ideas into small relatable steps.\n"
                "4. Praise effort, not just correct answers.\n"
                "SAFETY & REDIRECTION:\n"
                "1. Never discuss violence, politics, adult topics, or unsafe behavior.\n"
                "2. If asked something inappropriate, gently redirect: 'That's not something we need to explore right now. Let’s learn something fun instead!'\n"
                "CURRICULUM CONTEXT:\n"
                f"{curriculum_context}\n"
                "FORMATTING:\n"
                "1. DO NOT use any asterisks (*) or bolding (**). Keep text clean for text-to-speech.\n"
                "2. Use emojis in the text to keep it fun! 🌈✨"
            )
            
            messages = [{"role": "system", "content": system_instr}]
            
            # Add history in chronological order
            for chat in reversed(history_objs):
                messages.append({"role": "user", "content": chat.question})
                messages.append({"role": "assistant", "content": chat.answer})
            
            # Add current question
            messages.append({"role": "user", "content": question})

            # FreeFlow uses a similar structure to OpenAI
            response = client.chat(
                messages=messages,
                timeout=15.0
            )
            answer = response.content

            # Update subject progress
            if request.user.is_authenticated:
                progress.day_question_count += 1
                
                # Check for "NEXT_DAY" trigger OR 15 questions limit
                should_advance = "PROGRESS_UPDATE: NEXT_DAY" in answer or "PROGRESS_UPDATE: NEXT_CHAPTER" in answer or progress.day_question_count >= 15
                
                if should_advance:
                    progress.current_day += 1
                    progress.day_question_count = 0
                    answer = answer.replace("PROGRESS_UPDATE: NEXT_DAY", "").replace("PROGRESS_UPDATE: NEXT_CHAPTER", "").strip()
                
                progress.save()
                
                # Save conversation with day number
                Conversation.objects.create(
                    user=user,
                    topic=topic,
                    question=question,
                    answer=answer,
                    day_number=current_day
                )
            else:
                # Normal topic or guest
                Conversation.objects.create(
                    user=user,
                    topic=topic,
                    question=question,
                    answer=answer
                )

            return Response({"answer": answer}, status=status.HTTP_200_OK)

        except Exception as e:
            error_msg = str(e)
            
            # Specific handling for FreeFlow when no keys are valid
            if "All providers exhausted" in error_msg or "No providers configured" in error_msg:
                mock_answer = f"I'm here! I've switched to my 'Internal Intelligence' (Mock Mode) because your FreeFlow API keys (Groq/Gemini) are either missing or invalid. Please update your .env file to enable real AI responses!"
                
                Conversation.objects.create(
                    user=user,
                    topic=topic,
                    question=question,
                    answer=mock_answer
                )
                return Response({"answer": mock_answer, "is_mock": True}, status=status.HTTP_200_OK)

            # Friendly fallback if quota is exceeded or request times out
            if "insufficient_quota" in error_msg or "timeout" in error_msg.lower():
                mock_answer = f"I'd love to help you with '{question}', but I'm currently having a little trouble thinking (API Error/Timeout). Let me try again in a moment!"
                if "insufficient_quota" in error_msg:
                    mock_answer = f"I'd love to help you with '{question}', but my AI brain needs more energy (Quota Exceeded). Please check your FreeFlow provider keys!"
                
                # Still save the conversation for memory testing
                Conversation.objects.create(
                    user=user,
                    topic=topic,
                    question=question,
                    answer=mock_answer
                )
                return Response({"answer": mock_answer, "is_mock": True}, status=status.HTTP_200_OK)
                
            return Response(
                {"error": error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
