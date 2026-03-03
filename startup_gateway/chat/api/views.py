from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from chat.permissions import IsInvestor
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.exceptions import PermissionDenied
from pymongo.errors import PyMongoError

from chat.mongo_service import get_chat_service
from .serializers import (
    PaginationQuerySerializer,
    ConversationCreateSerializer,
    MessageCreateSerializer,
)

chat_service = get_chat_service()


def get_conversation_or_404(conversation_id, user_id):
    """
    Single DB call:
    - fetch conversation
    - permission check
    """
    try:
        conversation = chat_service.get_conversation(
            conversation_id=conversation_id,
            page=1,
            page_size=1
        )
    except PyMongoError:
        raise

    if not conversation:
        return None

    if user_id not in conversation["conversation"]["participants"]:
        raise PermissionDenied("You are not a participant of this conversation")

    return conversation


class ConversationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsInvestor()]
        return [IsAuthenticated()]

    def get_throttle_scope(self):
        return "chat_list" if self.request.method == "GET" else "chat_create"

    @extend_schema(
        parameters=[
            OpenApiParameter("page", OpenApiTypes.INT, description="Page number (default: 1)"),
            OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page (default: 20, max: 100)"),
        ],
        tags=["Chat - Conversations"],
        operation_id="list_conversations",
        summary="List conversations for authenticated user",
    )
    def get(self, request):
        serializer = PaginationQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        try:
            conversations = chat_service.list_conversations_for_user(
                user_id=request.user.id,
                page=serializer.validated_data["page"],
                page_size=serializer.validated_data["page_size"],
            )
            return Response(conversations)
        except PyMongoError:
            return Response({"detail": "Chat service temporarily unavailable"}, status=503)

    @extend_schema(
        request=ConversationCreateSerializer,
        tags=["Chat - Conversations"],
        operation_id="create_conversation",
        summary="Create new conversation",
    )
    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        try:
            conversation_id = chat_service.create_conversation(
                participants=serializer.validated_data["participants"],
                project_id=serializer.validated_data.get("project_id"),
                startup_id=serializer.validated_data.get("startup_id"),
            )
        except PyMongoError:
            return Response({"detail": "Chat service temporarily unavailable"}, status=503)

        return Response({"conversation_id": conversation_id}, status=201)


class ConversationMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]

    def get_throttle_scope(self):
        return "chat_list" if self.request.method == "GET" else "chat_send"

    @extend_schema(
        parameters=[
            OpenApiParameter("page", OpenApiTypes.INT),
            OpenApiParameter("page_size", OpenApiTypes.INT),
        ],
        tags=["Chat - Messages"],
        operation_id="list_messages",
        summary="List messages in conversation",
    )
    def get(self, request, conversation_id):
        serializer = PaginationQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        try:
            conversation = get_conversation_or_404(conversation_id, request.user.id)
            if not conversation:
                return Response({"detail": "Not found."}, status=404)

            messages_data = chat_service.get_conversation(
                conversation_id=conversation_id,
                page=serializer.validated_data["page"],
                page_size=serializer.validated_data["page_size"],
            )
            return Response(messages_data)

        except PermissionDenied:
            return Response({"detail": "Not found."}, status=404)
        except PyMongoError:
            return Response({"detail": "Chat service temporarily unavailable"}, status=503)

    @extend_schema(
        request=MessageCreateSerializer,
        tags=["Chat - Messages"],
        operation_id="send_message",
        summary="Send message via REST",
    )
    def post(self, request, conversation_id):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            conversation = get_conversation_or_404(conversation_id, request.user.id)
            if not conversation:
                return Response({"detail": "Not found."}, status=404)

            message = chat_service.create_message(
                conversation_id=conversation_id,
                sender_id=request.user.id,
                body=serializer.validated_data["body"],
                attachments=serializer.validated_data.get("attachments", []),
            )

            return Response({"message_id": message["_id"]}, status=201)

        except PermissionDenied:
            return Response({"detail": "Not found."}, status=404)
        except PyMongoError:
            return Response({"detail": "Chat service temporarily unavailable"}, status=503)


class MarkReadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_read"

    @extend_schema(
        tags=["Chat - Messages"],
        operation_id="mark_conversation_read",
        summary="Mark all messages as read",
    )
    def post(self, request, conversation_id):
        try:
            conversation = get_conversation_or_404(conversation_id, request.user.id)
            if not conversation:
                return Response({"detail": "Not found."}, status=404)

            chat_service.mark_messages_read(conversation_id, request.user.id)
            return Response(status=204)

        except PermissionDenied:
            return Response({"detail": "Not found."}, status=404)
        except PyMongoError:
            return Response({"detail": "Chat service temporarily unavailable"}, status=503)