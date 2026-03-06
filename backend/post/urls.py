from django.urls import URLPattern, path, include

URLPattern = [
    path(include('posts.urls')),
]