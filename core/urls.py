from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing_page'),
    path('teacher/', views.teacher_view, name='teacher_interface'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.account_view, name='account'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('ask/', views.AskAIView.as_view(), name='ask_ai'),
    path('history/', views.chat_history_view, name='chat_history'),
    path('history/delete/<int:chat_id>/', views.delete_chat_view, name='delete_chat'),
    path('health/', views.health_check, name='health_check'),
]
