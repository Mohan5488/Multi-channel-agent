from django.urls import path
from home.views import PromptInputView, ResumeWorkflowView #, StreamingWorkflowView, StreamingResumeView

urlpatterns = [
    path('messages/', PromptInputView.as_view(), name="messages"),
    path('resume/', ResumeWorkflowView.as_view(), name="resume_workflow"),
    # path('stream/', StreamingWorkflowView.as_view(), name="streaming_workflow"),
    # path('stream/resume/', StreamingResumeView.as_view(), name="streaming_resume"),
]
