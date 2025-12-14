from django.urls import path
from home.views import PromptInputView, ResumeWorkflowView, ThreadHistoryView, ThreadsListView
from home.views import ConnectGmailView, OAuth2CallbackView
from home.views import (
    ConnectCalendarView,
    CalendarOAuth2CallbackView,
    CreateEventView, GoogleLoginCallbackView
)
from home.views import LoginView, RegisterUser

urlpatterns = [
    path('login/', LoginView.as_view()),
    path('register/', RegisterUser.as_view()),
    path('google-login/', GoogleLoginCallbackView.as_view(), name='google_login_callback'),
    # path('accounts/google/login/callback/', GoogleLogin.as_view()),
    path('messages/', PromptInputView.as_view(), name="messages"),
    path('resume/', ResumeWorkflowView.as_view(), name="resume_workflow"),
    path('threads/<str:thread_id>/history/', ThreadHistoryView.as_view(), name="thread_history"),
    path('threads/', ThreadsListView.as_view(), name="threads_list"),

    path('connect_gmail/', ConnectGmailView.as_view(), name='connect_gmail'),
    path('oauth2callback/', OAuth2CallbackView.as_view(), name='oauth2callback'),

    path("connect_calendar/", ConnectCalendarView.as_view(), name="connect-calendar"),
    path("oauth2callback_calender/", CalendarOAuth2CallbackView.as_view(), name="calendar-oauth2callback"),
    path("calendar/create_event/", CreateEventView.as_view(), name="create-event"),
]
