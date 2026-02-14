from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrReadOnly(BasePermission):
    message = "Access denied."

    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)

        if user and user.is_staff:
            return True

        is_owner = bool(user and user.is_authenticated and getattr(obj.startup_profile, "user", None) == user)

        if request.method in SAFE_METHODS:
            if getattr(obj, "visibility", "public") == "public":
                return True

            self.message = "Only owner can view private/unlisted project."
            return is_owner

        if request.method == "DELETE":
            self.message = "Only owner can delete project."
        elif request.method in ("PUT", "PATCH"):
            self.message = "Only owner can update project."
        else:
            self.message = "Only owner can modify project."

        return is_owner


class IsAdminOrModerator(BasePermission):
    message = "Admin or moderator privileges required."

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.is_staff:
            return True

        try:
            if hasattr(user, 'roles'):
                user_roles = user.roles.values_list('name', flat=True)
                return 'admin' in user_roles or 'moderator' in user_roles
        except Exception:
            pass

        return False


class IsAdmin(BasePermission):
    message = "Admin privileges required."

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.is_staff:
            return True

        try:
            user_roles = user.roles.values_list('name', flat=True)
            return 'admin' in user_roles
        except Exception:
            return False


class IsSuperAdmin(BasePermission):
    message = "Super admin privileges required."

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return False

        return user.is_superuser


class CanCreateProject(BasePermission):
    message = "Only startup owner can create project."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return False

        startup_id = view.kwargs.get("startup_id")
        if not startup_id:
            return False    
        
        return (
            hasattr(user, "startup_profile") and
            user.startup_profile_id == int(startup_id)
            )
    
class CanModifyProject(BasePermission):
    message = "Only owner or admin can modify this project."

    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return False

        return obj.startup_profile.user == user

