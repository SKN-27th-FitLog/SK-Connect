from rest_framework.views import APIView #클래스 기반 뷰
from rest_framework.response import Response #api응답 보낼때 json형식으로 변환
from rest_framework import status #http응답 상태 코드 관리
from django.shortcuts import get_object_or_404 # 객체가 없을때 404에러 자동 발생
from .models import Posts #models.py파일에서 Posts라는 클래스(모델) 가져옴
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
)

class PostListView(APIView):
    def get(self, request): #게시글 목록을 가져와 클라이언트에게 보내줌

        #Posts.onjects는 Posts모델에 접근하기 위함
        posts = Posts.objects.select_related( #정참조 (foreignkey, onetoone)관계 데이터를 join을 통해 한꺼번에 미리 가져옴
            'post_cd',
            'status_cd',
            #'user_id'
        ).prefetch_related( #역참조(나를 참조하는)또는 다대다
            'imageurl_set',
            'maps_set'
        ).order_by('-created_at') #order_by : 정렬해라, -created_at : created_at 최신순

        serializer = PostListSerializer(posts, many=True) #데이터를 json으로 변환. 직렬화
        # 명세에 맞게 {"results": [...]} 형태로 래핑
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        #serializer.data : 직렬화 과정을 거쳐 최종적으로 json데이터로 변환된 결과물. 
        #serializer 자체는 객체일 뿐이므로 그 안에 들어있는 데이터 값을 보내야 하므로 serializer.data
        #Response 클래스를 통해 보냄(serializer.data를 받아 클라이언트 요구 형식으로 최종 렌더링하여)

class PostDetailView(APIView): #게시글 상세조회
    def get(self, request, pk):
        #게시글을 찾지 못하면(해당 pk없으면) 자동으로 404코드 반환
        post = get_object_or_404( 
            Posts.objects.select_related(
                'post_cd',
                'status_cd',
            ).prefetch_related(
                'imageurl_set',
                'maps_set'
            ),
            pk=pk # 특정 데이터를 하나만 집어내기 위한 목적. 인자로 들어온 id값을 통해
        )

        serializer = PostDetailSerializer(post)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostCreateView(APIView):

    def post(self, request):

        #사용자가 보낸 json데이터를 Serializer에 담음
        serializer = PostCreateSerializer(data=request.data) 

        #사용자 입력 검증
        if serializer.is_valid(): #비어있지 않은지 검사
            post = serializer.save() #비어있지 않다면 post 객체로 저장
            #serializer.save()를 호출하며 db에 row생김 + id번호 생성됨

            return Response(
                {"message": "게시글 생성 성공", "post_id": post.id}, #생성된 id번호 반환
                status=status.HTTP_201_CREATED #성공 코드
            )

        return Response( #is_valid()가 False일 경우 실행
            serializer.errors, # 왜 오류났는지 사용자에게 알려줌
            status=status.HTTP_400_BAD_REQUEST #400오류코드 반환
        )