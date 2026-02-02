from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrReadOnly(BasePermission):
    message = "Access denied."

    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)
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

