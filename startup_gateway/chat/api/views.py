from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from chat.mongo_service import get_chat_service
from .serializers import (
    PaginationQuerySerializer,
    ConversationCreateSerializer,
    MessageCreateSerializer,
)

chat_service = get_chat_service()


class ConversationAPIView(APIView):

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    
    def get_throttle_scope(self):
        if self.request.method == 'GET':
            return 'chat_list'
        return 'chat_create'

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "page",
                OpenApiTypes.INT,
                description="Page number (default: 1)"
            ),
            OpenApiParameter(
                "page_size",
                OpenApiTypes.INT,
                description="Items per page (default: 20, max: 100)"
            ),
        ],
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "conversation": {"type": "object"},
                        "last_message": {"type": "object"},
                        "unread_count": {"type": "integer"},
                    }
                }
            }
        },
        tags=["Chat - Conversations"],
        operation_id="list_conversations",
        summary="List conversations for authenticated user",
        description="Returns paginated list of conversations with last_message and unread_count"
    )
    def get(self, request):
        serializer = PaginationQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        conversations = chat_service.list_conversations_for_user(
            user_id=request.user.id,
            page=serializer.validated_data["page"],
            page_size=serializer.validated_data["page_size"],
        )

        return Response(conversations)
    
    @extend_schema(
        request=ConversationCreateSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string", "format": "uuid"}
                },
                "example": {
                    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        },
        tags=["Chat - Conversations"],
        operation_id="create_conversation",
        summary="Create new conversation",
        description="Create a conversation with participants, optionally linked to project/startup"
    )
    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_id = chat_service.create_conversation(
            participants=serializer.validated_data["participants"],
            project_id=serializer.validated_data.get("project_id"),
            startup_id=serializer.validated_data.get("startup_id"),
        )

        return Response(
            {"conversation_id": conversation_id},
            status=status.HTTP_201_CREATED,
        )


class ConversationMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    
    def get_throttle_scope(self):
        if self.request.method == 'GET':
            return 'chat_list'
        return 'chat_send'

    @extend_schema(
        parameters=[
            OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
            OpenApiParameter("page_size", OpenApiTypes.INT, description="Messages per page"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "conversation": {"type": "object"},
                    "messages": {"type": "array"},
                    "has_next": {"type": "boolean"},
                    "page": {"type": "integer"},
                    "page_size": {"type": "integer"},
                    "total": {"type": "integer"},
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                }
            }
        },
        tags=["Chat - Messages"],
        operation_id="list_messages",
        summary="List messages in conversation",
        description="Returns paginated messages. User must be participant."
    )
    def get(self, request, conversation_id):
        serializer = PaginationQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        conversation = chat_service.get_conversation(
            conversation_id=conversation_id,
            page=1,
            page_size=1
        )

        if not conversation:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if request.user.id not in conversation['conversation']['participants']:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages_data = chat_service.get_conversation(
            conversation_id=conversation_id,
            page=serializer.validated_data["page"],
            page_size=serializer.validated_data["page_size"],
        )

        return Response(messages_data)

    @extend_schema(
        request=MessageCreateSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"}
                },
                "example": {
                    "message_id": "65abc123def456789"
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                }
            }
        },
        tags=["Chat - Messages"],
        operation_id="send_message",
        summary="Send message via REST",
        description="Fallback method for sending messages (non-WebSocket). User must be participant."
    )
    def post(self, request, conversation_id):
        """Send a message via REST (fallback for non-WebSocket)."""
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = chat_service.get_conversation(
            conversation_id=conversation_id,
            page=1,
            page_size=1
        )

        if not conversation:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if request.user.id not in conversation['conversation']['participants']:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        message = chat_service.create_message(
            conversation_id=conversation_id,
            sender_id=request.user.id,
            body=serializer.validated_data["body"],
            attachments=serializer.validated_data.get("attachments", []),
        )

        return Response(
            {"message_id": message['_id']},
            status=status.HTTP_201_CREATED,
        )


class MarkReadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_read"

    @extend_schema(
        responses={
            204: None,
            404: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                }
            }
        },
        tags=["Chat - Messages"],
        operation_id="mark_conversation_read",
        summary="Mark all messages as read",
        description="Marks all unread messages in conversation as read for authenticated user"
    )
    def post(self, request, conversation_id):
        conversation = chat_service.get_conversation(
            conversation_id=conversation_id,
            page=1,
            page_size=1
        )

        if not conversation:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if request.user.id not in conversation['conversation']['participants']:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        chat_service.mark_messages_read(
            conversation_id=conversation_id,
            user_id=request.user.id,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)