
import django

from .views import TestFormView


if django.VERSION >= (2, 0):
    from django.urls import path, include
    urlpatterns = [
        path('test-form-view/', TestFormView.as_view()),
        path('martor/', include('martor.urls')),
    ]
else:
    from django.conf.urls import url, include
    urlpatterns = [
        url(r'^test-form-view/$', TestFormView.as_view()),
        url(r'^martor/', include('martor.urls')),
    ]
