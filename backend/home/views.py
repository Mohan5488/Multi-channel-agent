import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" 

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect
from google_auth_oauthlib.flow import Flow
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.dispatch import receiver
from allauth.account.signals import user_logged_in
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from .serializer import LoginSerializer, RegisterSerializer, UserDetailsSerializer
from .models import ServiceCredential
from email.mime.text import MIMEText
from src.agent.graph import run_workflow_api, resume_workflow_api
import base64
import uuid
import sqlite3
import os, json
class LoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        objs = User.objects.all()
        serializer = UserDetailsSerializer(objs, many=True)
        return Response({"data":serializer.data})
    
    def post(self, request):
        data = request.data
        serializer = LoginSerializer(data = data)

        if serializer.is_valid():
            username, password = serializer.validated_data['username'], serializer.validated_data['password']

            user = authenticate(username=username, password=password)
            print(user)

            if user:
                token, _ = Token.objects.get_or_create(user=user)

                return Response({
                    "message": "Login successful",
                    "token": token.key,
                    "user_id": user.id,
                    "username": user.username
                }, status=status.HTTP_200_OK)
            return Response({"message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.models import SocialAccount

from django.utils.timezone import now
class GoogleLoginCallbackView(APIView):
    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({'error': 'User not authenticated'}, status=401)

        token, _ = Token.objects.get_or_create(user=user)
        user.last_login = now()
        user.save(update_fields=['last_login'])

        # Optional: tag the session
        social_account = SocialAccount.objects.filter(user=user, provider='google').first()
        extra_data = social_account.extra_data if social_account else {}

        return Response({
            'message': 'Google login successful',
            'username': user.username,
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'google_info': extra_data,  # Add the full Google profile data
        })

@receiver(user_logged_in)
def create_auth_token(request, user, **kwargs):
    token, created = Token.objects.get_or_create(user=user)
    print("API Token:", token.key)

@receiver(user_logged_in)
def return_token_json(request, user, **kwargs):
    token, _ = Token.objects.get_or_create(user=user)
    print("LOGIN JSON API TOKEN RECIEVER -", token)
    return JsonResponse({
        "token": token.key,
        "username": user.username,
        "email": user.email
    })

class RegisterUser(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        serializer = RegisterSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
               "message" : "User created",
               "status" : True,
               "data" : serializer.validated_data
           }, status=status.HTTP_201_CREATED)
        return Response({
               "message" : serializer.errors,
               "status" : False
           }, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request):
        objs = User.objects.all()
        serializer = RegisterSerializer(objs, many=True)
        return Response(serializer.data) 



class PromptInputView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        """
        Start a new workflow or continue an existing one.
        """
        data = request.data
        user_prompt = data.get("user_prompt")
        thread_id = request.query_params.get('thread_id', str(uuid.uuid4()))
        user_id = request.user.id

        print(user_id)

        if not user_prompt:
            return Response(
                {"error": "user_prompt is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = run_workflow_api(user_prompt, user_id, thread_id)
            
            # Check if workflow was interrupted
            if result.get("status") == "interrupt":
                return Response({
                    "status": "interrupt",
                    "message": "Workflow interrupted - human input required",
                    "interrupt": result.get("interrupt"),
                    "thread_id": thread_id,
                    "state": result.get("state")
                }, status=status.HTTP_202_ACCEPTED)
            
            # Workflow completed successfully
            res = result.get("result", {})
            if res:
                return Response({
                    "status": res.get("status", "success"),
                    "message": res.get("message", "Workflow completed"),
                    "thread_id": thread_id,
                    "result": res
                })
            else:
                return Response({
                    "status": "completed",
                    "message": "Workflow completed",
                    "thread_id": thread_id,
                    "state": result
                })
                
        except Exception as e:
            return Response(
                {"error": f"Workflow failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResumeWorkflowView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        """
        Resume a workflow after providing human feedback.
        """
        data = request.data
        user_feedback = data.get("feedback")
        thread_id = request.query_params.get('thread_id')

        if not user_feedback:
            return Response(
                {"error": "feedback is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not thread_id:
            return Response(
                {"error": "thread_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = resume_workflow_api(user_feedback, thread_id)
            
            # Check if workflow was interrupted again
            if result.get("status") == "interrupt":
                return Response({
                    "status": "interrupt",
                    "message": "Workflow interrupted again - additional input required",
                    "interrupt": result.get("interrupt"),
                    "thread_id": thread_id,
                    "state": result.get("state")
                }, status=status.HTTP_202_ACCEPTED)
            
            # Workflow completed successfully
            res = result.get("result", {})
            if res:
                return Response({
                    "status": res.get("status", "success"),
                    "message": res.get("message", "Workflow completed"),
                    "thread_id": thread_id,
                    "result": res
                })
            else:
                return Response({
                    "status": "completed",
                    "message": "Workflow completed",
                    "thread_id": thread_id,
                    "state": result
                })
                
        except Exception as e:
            return Response(
                {"error": f"Workflow resume failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ThreadHistoryView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, thread_id):
        """
        Get conversation history for a specific thread_id.
        """
        if not thread_id:
            return Response(
                {"error": "thread_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from src.agent.graph import create_workflow, serialize_state
            
            # Create workflow instance
            app = create_workflow()
            config = {"configurable": {"thread_id": thread_id}}
            
            # Get the current state from checkpoints
            current_state = app.get_state(config)
            
            if not current_state or not current_state.values:
                return Response({
                    "thread_id": thread_id,
                    "message": "No conversation history found for this thread",
                    "history": [],
                    "state": {}
                })
            
            # Serialize the state for JSON response
            serialized_state = serialize_state(current_state.values)
            
            # Extract messages from state
            messages = current_state.values.get("messages", [])
            
            # Format messages for frontend
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    "type": msg.__class__.__name__,
                    "content": msg.content if hasattr(msg, 'content') else str(msg),
                })
            
            return Response({
                "thread_id": thread_id,
                "message": "Conversation history retrieved successfully",
                "history": formatted_messages,
                "state": serialized_state,
                "total_messages": len(formatted_messages)
            })
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve history: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ThreadHistoryView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, thread_id):
        """
        Get conversation history for a specific thread_id.
        """
        if not thread_id:
            return Response(
                {"error": "thread_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from src.agent.graph import create_workflow, serialize_state
            
            # Create workflow instance
            app = create_workflow()
            config = {"configurable": {"thread_id": thread_id}}
            
            # Get the current state from checkpoints
            current_state = app.get_state(config)
            
            if not current_state or not current_state.values:
                return Response({
                    "thread_id": thread_id,
                    "message": "No conversation history found for this thread",
                    "history": [],
                    "state": {}
                })
            
            # Serialize the state for JSON response
            serialized_state = serialize_state(current_state.values)
            
            # Extract messages from state
            messages = current_state.values.get("messages", [])
            
            # Format messages for frontend
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    "type": msg.__class__.__name__,
                    "content": msg.content if hasattr(msg, 'content') else str(msg),
                    "timestamp": getattr(msg, 'timestamp', None)
                })
            
            return Response({
                "thread_id": thread_id,
                "message": "Conversation history retrieved successfully",
                "history": formatted_messages,
                "state": serialized_state,
                "total_messages": len(formatted_messages)
            })
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve history: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ThreadsListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        """
        Return a list of distinct thread_ids from the LangGraph SQLite checkpointer.
        """
        try:
            conn = sqlite3.connect("checkpoints.db")
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            thread_ids = set()

            # Try common LangGraph tables first
            for table in ["checkpoints", "checkpoint_writes"]:
                try:
                    cur.execute(f"SELECT DISTINCT thread_id FROM {table}")
                    rows = cur.fetchall()
                    for r in rows:
                        if r["thread_id"]:
                            thread_ids.add(str(r["thread_id"]))
                except Exception:
                    # Table may not exist; continue to next strategy
                    pass

            # If still empty, discover any table that has a thread_id column
            if not thread_ids:
                cur.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """
                )
                tables = [row[0] for row in cur.fetchall()]
                for tbl in tables:
                    try:
                        cur.execute(f"PRAGMA table_info({tbl})")
                        cols = [c[1] for c in cur.fetchall()]  # col names
                        if "thread_id" in cols:
                            cur.execute(f"SELECT DISTINCT thread_id FROM {tbl}")
                            for r in cur.fetchall():
                                if r[0]:
                                    thread_ids.add(str(r[0]))
                    except Exception:
                        continue

            conn.close()

            

            return Response({
                "threads": thread_ids,
                "count": len(thread_ids)
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to list threads: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",  # optional
    "https://www.googleapis.com/auth/calendar",
]
REDIRECT_URI = "http://127.0.0.1:8000/v1/oauth2callback"

class ConnectGmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get("user_id")
        print(user_id)
        flow = Flow.from_client_secrets_file(
            'src/agent/nodes/client_secret.json',
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        state = json.dumps({'user_id': user_id})
        auth_url, _ = flow.authorization_url(
            access_type='offline', 
            include_granted_scopes=False,
            prompt='consent',     
            state=state
        )

        print("auth_url-",auth_url)
        return Response({"auth_url": auth_url})

class OAuth2CallbackView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        state = json.loads(request.GET.get("state", "{}"))
        print(state)
        user_id = state.get("user_id")

        flow = Flow.from_client_secrets_file(
            'src/agent/nodes/client_secret.json',
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        creds = flow.credentials

        ServiceCredential.objects.update_or_create(
            user_id=user_id,
            service="gmail",
            defaults={
                "data": {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                    "expiry": creds.expiry.isoformat() if creds.expiry else None
                }
            }
        )

        # return Response({"status": "success", "message": "Gmail connected!"})
        return redirect("http://localhost:5173/test")

REDIRECT_URI_CALENDER = "http://127.0.0.1:8000/v1/oauth2callback_calender"

class ConnectCalendarView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get("user_id")
        flow = Flow.from_client_secrets_file(
            'src/agent/nodes/calender/credentials.json',
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI_CALENDER
        )

        state = json.dumps({'user_id': user_id})
        auth_url, _ = flow.authorization_url(
            access_type='offline',     # request refresh token
            include_granted_scopes=False,
            prompt='consent',
            state=state
        )
        print("AUTHORIZATION URL CREATED")
        print("auth_url-",auth_url)
        return Response({"auth_url": auth_url})


class CalendarOAuth2CallbackView(APIView):
    def get(self, request):
        state = json.loads(request.GET.get("state", "{}"))
        user_id = state.get("user_id")

        flow = Flow.from_client_secrets_file(
            'src/agent/nodes/calender/credentials.json',
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI_CALENDER
        )

        flow.fetch_token(authorization_response=request.build_absolute_uri())
        creds = flow.credentials

        ServiceCredential.objects.update_or_create(
            user_id=user_id,
            service="google_calendar",
            defaults={
                "data": {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                    "expiry": creds.expiry.isoformat() if creds.expiry else None
                }
            }
        )

        return redirect("http://localhost:5173/test?status=success&service=calendar")


TOKEN_DIR = "calendar_tokens"

def load_calendar_credentials(user_id):
    path = os.path.join(TOKEN_DIR, f"{user_id}.json")
    if not os.path.exists(path):
        return None
    data = json.load(open(path))
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes")
    )
    return creds

def ensure_valid(creds):
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

from googleapiclient.discovery import build
from rest_framework.views import APIView

class CreateEventView(APIView):
    def post(self, request):
        user_id = 1
        creds = load_calendar_credentials(user_id)
        if not creds:
            return Response({"status": "error", "message": "User not connected."})

        creds = ensure_valid(creds)
        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': request.data.get("summary", "Test Event"),
            'description': request.data.get("description", ""),
            'start': {'dateTime': request.data.get("start"), 'timeZone': 'UTC+5:30'},
            'end': {'dateTime': request.data.get("end"), 'timeZone': 'UTC+5:30'},
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return Response({"status": "success", "event_id": event.get("id")})
