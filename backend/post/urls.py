from django.urls import URLPattern, path, include

URLPattern = [
    path('api/', include('posts.urls')),
]