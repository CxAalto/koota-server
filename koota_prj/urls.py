"""koota_prj URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth import views as auth_views

from kdata import views as kviews
from kdata import views_admin

import oxford2016.views

urlpatterns = [ ]

if 'admin' in settings.WEB_COMPONENTS:
  urlpatterns += [
    url(r'^admin/', admin.site.urls),
   ]

if 'ui' in settings.WEB_COMPONENTS:
  urlpatterns += [
    url(r'^login/$', views_admin.KootaLoginView.as_view(),  name='login2'),
    url(r'^register/$', views_admin.RegisterView.as_view(), name='register-user'),
    url(r'^change-password/$', views_admin.KootaPasswordChangeView.as_view(), name='change-password'),
    url(r'^2fa/$',          views_admin.otp_config, name='otp-config'),
    url(r'^2fa/2fa-qr.png', views_admin.otp_qr,     name='otp-qr'),

    url(r'^oxford/', oxford2016.views.main,     name='oxford2016'),


    url(r'^', include('django.contrib.auth.urls')),
  ]


urlpatterns += [
    url(r'^privacy/', RedirectView.as_view(url=settings.SITE_PRIVACY_URL),
        name='site-privacy'),
    url(r'^', include('kdata.urls')),
]
