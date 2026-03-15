from rest_framework import generics
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from .models import Posts 
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
)

class PostListView(generics.ListAPIView): 
    serializer_class = PostListSerializer

    def get_queryset(self):
        return Posts.objects.select_related(
            'post_cd', 
            'status_cd', 
            'user_id'
        ).prefetch_related(
            'imageurl_set' # 역참조  _set
        ).order_by('-created_at')


class PostDetailView(generics.RetrieveAPIView): 
    queryset = Posts.objects.all()
    serializer_class = PostDetailSerializer
    lookup_field = 'id' 

    def get_queryset(self):
        return Posts.objects.select_related(
            'post_cd', 'status_cd', 'user_id'
        ).prefetch_related('imageurl_set')


class PostCreateView(generics.CreateAPIView): 
    queryset = Posts.objects.all()
    serializer_class = PostCreateSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def perform_create(self, serializer):
        serializer.save()