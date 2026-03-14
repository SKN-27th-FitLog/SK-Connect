from rest_framework import generics
from .models import Post
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
)

class PostListView(generics.ListAPIView): #게시글 리스트 조회
    queryset = Post.objects.all()
    serializer_class = PostListSerializer

    #Posts.onjects는 Posts모델에 접근하기 위함
    posts = Post.objects.select_related( #정참조 (foreignkey, onetoone)관계 데이터를 join을 통해 한꺼번에 미리 가져옴
        'post_cd',
        'status_cd',
        #'user_id'
    ).prefetch_related( #역참조(나를 참조하는)또는 다대다
        'imageurl_set',
        'maps_set'
    ).order_by('-created_at') #order_by : 정렬해라, -created_at : created_at 최신순

    def get_queryset(self):
        return super().get_queryset()



class PostDetailView(generics.ListAPIView): #게시글 상세조회
    queryset = Post.objects.all()
    serializer_class = PostDetailSerializer

    



class PostCreateView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostCreateSerializer

