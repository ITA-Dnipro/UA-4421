"""
Django REST Framework views - TASK SPECIFICATION COMPLIANT.

- Uses UUID for conversation_id
- Uses "body" instead of "content" for messages
- Uses "meta" instead of "metadata"
- Only 1-on-1 conversations
- Only investors can initiate
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..mongo_service import get_chat_service
from .serializers import (
    ConversationSerializer,
    CreateConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
    UpdateMessageStatusSerializer,
    MessageListSerializer,
    ConversationListSerializer,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_conversation(request):
    """
    Create a new 1-on-1 conversation.
    Only investors can create conversations.
    
    POST /api/chat/conversations/
    Body: {
        "recipient_id": 123  # User ID (should be startup)
    }
    
    Returns: conversation with UUID conversation_id
    """
    serializer = CreateConversationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    chat_service = get_chat_service()
    
    try:
        # Returns UUID conversation_id
        conversation_id = chat_service.create_conversation(
            initiator_id=request.user.id,
            recipient_id=serializer.validated_data['recipient_id']
        )
        
        # Retrieve the conversation
        conversation = chat_service.get_conversation(conversation_id)
        
        return Response(
            ConversationSerializer(conversation).data,
            status=status.HTTP_201_CREATED
        )
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_conversations(request):
    """
    List user's conversations.
    
    GET /api/chat/conversations/?limit=50&skip=0
    """
    serializer = ConversationListSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    chat_service = get_chat_service()
    
    try:
        conversations = chat_service.get_user_conversations(
            user_id=request.user.id,
            limit=data['limit'],
            skip=data['skip']
        )
        
        return Response(
            ConversationSerializer(conversations, many=True).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_detail(request, conversation_id):
    """
    Get conversation details by UUID.
    
    GET /api/chat/conversations/<uuid:conversation_id>/
    """
    chat_service = get_chat_service()
    
    try:
        # conversation_id is UUID string
        conversation = chat_service.get_conversation(conversation_id)
        
        if not conversation:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is a participant
        if request.user.id not in conversation['participants']:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response(
            ConversationSerializer(conversation).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_with_user(request, user_id):
    """
    Get or find conversation with specific user.
    
    GET /api/chat/conversations/with/<user_id>/
    """
    chat_service = get_chat_service()
    
    try:
        conversation = chat_service.get_conversation_between_users(
            user1_id=request.user.id,
            user2_id=user_id
        )
        
        if not conversation:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(
            ConversationSerializer(conversation).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """
    Send a message in a conversation.
    
    POST /api/chat/messages/
    Body: {
        "conversation_id": "uuid-string",
        "body": "Hello!",  // "body" NOT "content"
        "attachments": [{
            "upload_id": "...",  // REQUIRED
            "url": "...",
            "type": "image"
        }],  // optional
        "meta": {}  // optional, "meta" NOT "metadata"
    }
    """
    serializer = SendMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    chat_service = get_chat_service()
    
    try:
        # conversation_id is UUID string
        message_id = chat_service.send_message(
            conversation_id=str(data['conversation_id']),
            sender_id=request.user.id,
            body=data['body'],  # "body" NOT "content"
            attachments=data.get('attachments'),
            meta=data.get('meta', {})  # "meta" NOT "metadata"
        )
        
        # Get the created message (last one in conversation)
        messages = chat_service.get_messages(
            conversation_id=str(data['conversation_id']),
            limit=1
        )
        
        if messages:
            # Return last message (newest)
            newest_message = max(messages, key=lambda m: m.get('created_at', ''))
            return Response(
                MessageSerializer(newest_message).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {'id': message_id},
                status=status.HTTP_201_CREATED
            )
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_messages(request, conversation_id):
    """
    List messages in a conversation by UUID.
    
    GET /api/chat/conversations/<uuid:conversation_id>/messages/?limit=50&skip=0&before_id=...
    """
    serializer = MessageListSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    chat_service = get_chat_service()
    
    # Verify conversation exists and user is participant
    conversation = chat_service.get_conversation(conversation_id)
    if not conversation:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.user.id not in conversation['participants']:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        messages = chat_service.get_messages(
            conversation_id=conversation_id,  # UUID string
            limit=data['limit'],
            skip=data['skip'],
            before_id=data.get('before_id')
        )
        
        return Response(
            MessageSerializer(messages, many=True).data,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_message_status(request, message_id):
    """
    Update message status (sent → delivered → read).
    
    PATCH /api/chat/messages/<message_id>/status/
    Body: {"status": "read"}
    """
    serializer = UpdateMessageStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    chat_service = get_chat_service()
    
    try:
        success = chat_service.update_message_status(
            message_id,
            serializer.validated_data['status']
        )
        
        if success:
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request, conversation_id):
    """
    Get count of unread messages in a conversation.
    
    GET /api/chat/conversations/<uuid:conversation_id>/unread/
    """
    chat_service = get_chat_service()
    
    try:
        count = chat_service.get_unread_count(conversation_id, request.user.id)
        
        return Response(
            {'count': count},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request, conversation_id):
    """
    Mark all messages in conversation as read.
    
    POST /api/chat/conversations/<uuid:conversation_id>/read/
    """
    chat_service = get_chat_service()
    
    # Verify user is in conversation
    conversation = chat_service.get_conversation(conversation_id)
    if not conversation:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.user.id not in conversation['participants']:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        count = chat_service.mark_all_as_read(conversation_id, request.user.id)
        
        return Response(
            {
                'status': 'success',
                'messages_updated': count
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
