from django.urls import path
from home.views import PromptInputView, ResumeWorkflowView, ThreadHistoryView, ThreadsListView #, StreamingWorkflowView #, StreamingResumeView

urlpatterns = [
    path('messages/', PromptInputView.as_view(), name="messages"),
    path('resume/', ResumeWorkflowView.as_view(), name="resume_workflow"),
    path('threads/<str:thread_id>/history/', ThreadHistoryView.as_view(), name="thread_history"),
    path('threads/', ThreadsListView.as_view(), name="threads_list"),
    # path('stream/', StreamingWorkflowView.as_view(), name="streaming_workflow"),
    # path('stream/resume/', StreamingResumeView.as_view(), name="streaming_resume"),
]
