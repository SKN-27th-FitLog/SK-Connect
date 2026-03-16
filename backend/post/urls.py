from django.urls import path
from .views import PostListView, PostDetailView, PostCreateView

urlpatterns = [
    # 명세: /posts
    path("posts", PostListView.as_view(), name="post-list"),
    # 명세: /posts/{feed_id}
    path("posts/<int:id>", PostDetailView.as_view(), name="post-detail"),
    # 명세: /api/posts (POST)
    path("api/posts", PostCreateView.as_view(), name="post-create"),
]