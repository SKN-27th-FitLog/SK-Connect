from django.urls import path
from .views import PostListView, PostDetailView, PostCreateView

urlpatterns = [
    # 명세: /posts
    path("posts", PostListView.as_view(), name="post-list"),
    # 호환: /posts/
    path("posts/", PostListView.as_view(), name="post-list-slash"),
    # 명세: /posts/{feed_id}
    path("posts/<int:pk>", PostDetailView.as_view(), name="post-detail"),
    # 호환: /posts/{feed_id}/
    path("posts/<int:pk>/", PostDetailView.as_view(), name="post-detail-slash"),
    # 명세: /api/posts (POST)
    path("api/posts", PostCreateView.as_view(), name="post-create"),
    # 호환: /api/posts/
    path("api/posts/", PostCreateView.as_view(), name="post-create-slash"),
]