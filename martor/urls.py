import django
from .views import (markdownfy_view,
                    markdown_imgur_uploader,
                    markdown_search_user)


if django.VERSION >= (2, 0):
    from django.urls import path
    urlpatterns = [
        path('markdownify/', markdownfy_view, name='martor_markdownfy'),
        path('uploader/', markdown_imgur_uploader, name='imgur_uploader'),
        path('search-user/', markdown_search_user, name='search_user_json'),
    ]
else:
    from django.conf.urls import url
    urlpatterns = [
        url(r'^markdownify/$', markdownfy_view, name='martor_markdownfy'),
        url(r'^uploader/$', markdown_imgur_uploader, name='imgur_uploader'),
        url(r'^search-user/$', markdown_search_user, name='search_user_json'),
    ]
