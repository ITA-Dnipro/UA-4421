from rest_framework import permissions


class IsInvestor(permissions.BasePermission):
    """
    Permission: Only investors can create conversations.

    Startups can only participate in conversations created by investors.
    """

    message = "Only investors can create conversations"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.roles.filter(name='investor').exists()


class IsParticipant(permissions.BasePermission):
    """
    Permission: User must be a participant in the conversation.
    """

    message = "You are not a participant in this conversation"

    def has_object_permission(self, request, view, obj):
        # obj = conversation dict from MongoDB
        return request.user.id in obj.get('participants', [])