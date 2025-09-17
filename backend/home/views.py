from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import StreamingHttpResponse
from src.agent.graph import run_workflow_api, resume_workflow_api #, run_workflow_streaming #resume_workflow_streaming
import uuid
import json
import time
import asyncio
import sqlite3

class PromptInputView(APIView):
    def post(self, request):
        """
        Start a new workflow or continue an existing one.
        """
        data = request.data
        user_prompt = data.get("user_prompt")
        thread_id = request.query_params.get('thread_id', str(uuid.uuid4()))

        if not user_prompt:
            return Response(
                {"error": "user_prompt is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = run_workflow_api(user_prompt, thread_id)
            
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


# class StreamingWorkflowView(APIView):
#     def post(self, request):
#         """
#         Start a streaming workflow with real-time updates via Server-Sent Events.
#         """
#         data = request.data
#         user_prompt = data.get("user_prompt")
#         thread_id = request.query_params.get('thread_id', str(uuid.uuid4()))

#         if not user_prompt:
#             return Response(
#                 {"error": "user_prompt is required"}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         def event_stream():
#             async def async_event_stream():
#                 try:
#                     async for update in run_workflow_streaming(user_prompt, thread_id):
#                         # Format as Server-Sent Event
#                         event_data = json.dumps(update)
#                         yield f"data: {event_data}\n\n"
                        
#                         # Add small delay to prevent overwhelming the client
#                         await asyncio.sleep(0.1)
                        
#                         # If interrupt, stop streaming and wait for resume
#                         if update.get("type") == "interrupt":
#                             break
                            
#                 except Exception as e:
#                     error_data = {
#                         "type": "error",
#                         "message": f"Streaming failed: {str(e)}",
#                         "error": str(e)
#                     }
#                     yield f"data: {json.dumps(error_data)}\n\n"
            
#             # Convert async generator to regular generator
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
#             try:
#                 async_gen = async_event_stream()
#                 while True:
#                     try:
#                         yield loop.run_until_complete(async_gen.__anext__())
#                     except StopAsyncIteration:
#                         break
#             finally:
#                 loop.close()

#         response = StreamingHttpResponse(
#             event_stream(),
#             content_type='text/event-stream'
#         )
#         response['Cache-Control'] = 'no-cache'
#         response['Access-Control-Allow-Origin'] = '*'
#         response['Access-Control-Allow-Headers'] = 'Cache-Control'
        
#         return response


class ThreadHistoryView(APIView):
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


# class StreamingResumeView(APIView):
#     def post(self, request):
#         """
#         Resume a streaming workflow with real-time updates.
#         """
#         data = request.data
#         user_feedback = data.get("feedback")
#         thread_id = request.query_params.get('thread_id')

#         if not user_feedback:
#             return Response(
#                 {"error": "feedback is required"}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         if not thread_id:
#             return Response(
#                 {"error": "thread_id is required"}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         def event_stream():
#             try:
#                 for update in resume_workflow_streaming(user_feedback, thread_id):
#                     # Format as Server-Sent Event
#                     event_data = json.dumps(update)
#                     yield f"data: {event_data}\n\n"
                    
#                     # Add small delay to prevent overwhelming the client
#                     time.sleep(0.1)
                    
#                     # If interrupt, stop streaming and wait for resume
#                     if update.get("type") == "interrupt":
#                         break
                        
#             except Exception as e:
#                 error_data = {
#                     "type": "error",
#                     "message": f"Streaming resume failed: {str(e)}",
#                     "error": str(e)
#                 }
#                 yield f"data: {json.dumps(error_data)}\n\n"

#         response = StreamingHttpResponse(
#             event_stream(),
#             content_type='text/event-stream'
#         )
#         response['Cache-Control'] = 'no-cache'
#         response['Access-Control-Allow-Origin'] = '*'
#         response['Access-Control-Allow-Headers'] = 'Cache-Control'
        
#         return response


class ThreadHistoryView(APIView):
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
