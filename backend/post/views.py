from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Posts
from .serializers import PostSerializer

class PostListView(APIView):
    """
    게시글 전체 목록을 가져오는 API
    """
    def get(self, request):
        # 1. DB 조회를 한 번에 처리합니다.
        # select_related: ForeignKey 관계 (1:1, N:1) - 카테고리, 유저, 지도
        # prefetch_related: 역참조 관계 (1:N) - 이미지 리스트
        posts = Posts.objects.select_related(
            'post_category_cd',  # 카테고리
            #'user_id',           # 작성자 
            'map_id'             # 지도 정보 
        ).prefetch_related(
            'postimage_set'      # 이미지 리스트 (역참조)
        ).all().order_by('-created_at') # 최신순 정렬

        # 2. 데이터를 시리얼라이저에 
        serializer = PostSerializer(posts, many=True)

        # 3. 명세서에 맞는 결과 반환
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostDetailView(APIView):
    """
    특정 게시글 하나만 가져오는 API
    """
    def get(self, request, pk):
        try:
            # 관련 데이터를 미리 가져옴
            post = Posts.objects.select_related(
                'post_category_cd'
            ).prefetch_related(
                'postimage_set'
            ).get(pk=pk)
            
            serializer = PostSerializer(post)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Posts.DoesNotExist:
            return Response(
                {"error": "게시글을 찾을 수 없습니다."}, 
                status=status.HTTP_404_NOT_FOUND
            )