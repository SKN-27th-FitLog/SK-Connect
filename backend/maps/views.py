from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Maps

class MapMarkersView(APIView):

    def get(self, request):

        maps = Maps.objects.select_related(
            "post",
            "category"
        )

        markers = []

        for m in maps:

            # 게시글 마커
            if m.post:
                markers.append({
                    "type": "post",
                    "post_id": m.post.id,
                    "title": m.post.title,
                    "content": m.post.content,
                    "address_cd": m.address_cd,
                    "latitude": m.latitude,
                    "longitude": m.longitude,
                    "category": m.category.name if m.category else None
                })

            # 맛집 마커
            else:
                markers.append({
                    "type": "restaurant",
                    "name": m.name,
                    "address_cd": m.address_cd,
                    "latitude": m.latitude,
                    "longitude": m.longitude,
                    "category": m.category.name if m.category else None,
                    "signature_menu": m.signature_menu
                })

        return Response({"markers": markers})