from django.urls import path
from .views import SavedItemView

urlpatterns = [
    path('users/<int:user_id>/saved/', SavedItemView.as_view(), name='user-saved-create'),
    path('users/<int:user_id>/saved/<int:saved_id>/', SavedItemView.as_view(), name='user-saved-delete'),
]