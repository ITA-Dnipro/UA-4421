from django.urls import path
from .views import SavedItemView

urlpatterns = [
    path('api/users/<int:user_id>/saved/', SavedItemView.as_view(), name='user-saved-create'),
    path('api/users/<int:user_id>/saved/<int:saved_id>/', SavedItemView.as_view(), name='user-saved-delete'),
]