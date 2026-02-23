import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from freeflow_llm import FreeFlowClient
from dotenv import load_dotenv
from .models import Conversation, UserProfile
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Initialize FreeFlow Client
def get_freeflow_client():
    load_dotenv()
    return FreeFlowClient()

def teacher_view(request):
    """Render the AI Teacher interface."""
    from django.shortcuts import render
    return render(request, 'core/teacher.html')

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
    """API endpoint to get chat history for the authenticated user or guest session."""
    if request.user.is_authenticated:
        history = Conversation.objects.filter(user=request.user).order_by('-created_at')[:20]
    else:
        # Guests see no history or only their session's history if we implement it later
        # For now, guests start fresh on every visit to ensure privacy
        return JsonResponse({"history": []})
        
    data = [
        {
            "id": h.id,
            "question": h.question, 
            "answer": h.answer, 
            "timestamp": h.created_at.isoformat()
        }
        for h in history
    ]
    return JsonResponse({"history": data})

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
            
            # Example Limit for Free Tier (e.g., 20 questions)
            if profile.plan == 'FREE' and profile.questions_asked >= 20:
                return Response(
                    {"error": "Free tier limit reached. Please upgrade!", "limit_reached": True},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            profile.questions_asked += 1
            profile.save()

        try:
            # Call FreeFlow LLM API
            client = get_freeflow_client()
            
            # Fetch recent conversation history for memory (last 5 exchanges)
            history_objs = Conversation.objects.filter(user=user).order_by('-created_at')[:5]
            messages = [{"role": "system", "content": f"You are a friendly AI Teacher for small kids. The current topic is {topic}. \nRules:\n1. Keep answers very short, simple, and exciting!\n2. Use lots of emojis! 🌈✨\n3. DO NOT use any asterisks (*) or bolding (**). Keep the text clean and easy to read.\n4. Use a warm, encouraging tone."}]
            
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

            # Save the conversation
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
