from django.conf import settings
from django.conf.urls import url, include
from django.views.generic import TemplateView

from kdata import group
from kdata import survey
from kdata import views as kviews
from kdata import views_admin
from kdata import views_data
from kdata.devices import aware
from kdata.devices import facebook
from kdata.devices import funf
from kdata.devices import instagram
from kdata.devices import twitter
from kdata.devices.muratabsn import MurataBSN, murata_calibrate
from kdata.devices.purplerobot import PurpleRobot
from kdata.devices.actiwatch import Actiwatch

# These URLs relate to receiving data, and should be usable by the
# write-only domain (not quite there yet, but...)
# pylint: disable=invalid-name
urls_data = [
    # Purple Robot - different API
    url(r'^post/purple/?(?P<device_id>\w+)?/?$', kviews.post,
        dict(device_class=PurpleRobot), name='post-purple'),
    # Actigraphs - process and remove data
    url(r'^post/actiwatch/?(?P<device_id>\w+)?/?$', kviews.post,
        dict(device_class=Actiwatch), name='post-actiwatch'),
    # Generic POST url.
    url(r'^post/?(?P<device_id>[A-Fa-f0-9]+)?/?$', kviews.post, name='post'),
    # Murata sleep sensor: this has a hard-coded POST URL.
    url(r'^data/push/$', kviews.post, dict(device_class=MurataBSN),
        name='post-MurataBSN'),
    # Murata sleep sensor, calibration
    url(r'^firmware/device/(?P<mac_addr>[^/]+)/?$', murata_calibrate,
        name='MurataBSN-calibrate'),
    # Generic config, for our own app (not really used now)
    url(r'^config$', kviews.config, name='config'),
    # Funf
    url(r'^funf/post1/(?P<device_id>[A-Fa-f0-9]+)?/?$', kviews.post,
        dict(device_class=funf.FunfJournal),
        name='funf-journal-post'),
    # AWARE
    # Note: these do require write-connection
    url(r'^(?:(?P<indexphp>index\.php)/)?aware/', include(aware.urlpatterns)),
    url(r'^(?P<indexphp>index\.php)/', include(aware.urlpatterns_fixed)),

    ]

urls_device = [
    url(r'^$', kviews.DeviceListView.as_view(), name='device-list'),
    # /public_id/config
    url(r'^(?P<public_id>[0-9a-fA-F]*)/config$', kviews.DeviceConfig.as_view(),
        name='device-config'),
    # URL for marking that a subject does not have this device
    url(r'^(?P<public_id>[0-9a-fA-F]*)/mark-device/dont-have',
        kviews.mark_device, dict(operation="dont-have"),
        name='mark-device-dont-have'),
    url(r'^(?P<public_id>[0-9a-fA-F]*)/mark-device/not-linking',
        kviews.mark_device, dict(operation="not-linking"),
        name='mark-device-not-linking'),
    # /public_id/qr.png
    url(r'^(?P<public_id>[0-9a-fA-F]*)/qr.png$', kviews.device_qrcode,
        name='device-qr'),
    # /public_id/upload
    url(r'^(?P<public_id>[0-9a-fA-F]*)/upload$', views_admin.upload,
        name='device-upload'),
    # /public_id/json
    url(r'^(?P<public_id>[0-9a-fA-F]*)/json$', views_data.device_detail_json,
        name='device-detail-json'),
    # /public_id/
    url(r'^(?P<public_id>[0-9a-fA-F]*)/$', views_data.DeviceDetail.as_view(),
        name='device'),
    # /public_id/Converter.format
    url(r'^(?P<public_id>[0-9a-fA-F]*)/(?P<converter>\w+)\.?(?P<format>[\w-]+)?',
        views_data.device_data,
        name='device-data'),
]

urls_subject = [
    # /create
    url(r'^create/$', kviews.DeviceCreate.as_view(),
        name='device-create'),
]

urls_ui = [
    # Device UI
    #
    # /devices/
    url(r'^devices/', include(urls_subject)),
    url(r'^devices/', include(urls_device)),

    # Various admin things
    url(r'^stats/', views_admin.stats),
    url(r'^time/', views_admin.current_time),

    # Misc
    #
    # Purple Robot log POST url (doesn't work)
    url(r'^log$', kviews.log, name='log'),
    # Surveys
    url(r'^survey/take/(?P<token>[\w]*)', survey.take_survey, name='survey-take'),

    # Group interface

    # /group/
    url(r'^group/$', group.group_join, name='group-join'),
    # /group/name/
    url(r'^group/(?P<group_name>[\w-]+)/$', group.group_detail, name='group-detail'),
    # /group/name/stats
    url(r'^group/(?P<group_name>[\w-]+)/stats/?$',
        group.group_stats, name='group-stats'),
    # /group/name/config
    url(r'^group/(?P<group_name>[\w-]+)/config/?$',
        group.GroupUpdate.as_view(), name='group-update'),
    # /group/name/converter/json
    url(r'^group/(?P<group_name>[\w-]+)/(?P<converter>\w+)/json$',
        group.group_data_json, name='group-data-json'),
    # /group/name/converter(.ext)
    url(r'^group/(?P<group_name>[\w-]+)/(?P<converter>\w+)\.?(?P<format>[\w-]+)?$',
        group.group_data, name='group-data'),
    # /group/name/user-create/
    url(r'^group/(?P<group_name>[\w-]+)/user-create/$',
        group.group_user_create, name='group-user-create'),
    # Subject related
    # /group/name/subjNN/
    url(r'^group/(?P<group_name>[\w-]+)/subj(?P<gs_id>[0-9]+)/$',
        group.group_subject_detail, name='group-subject-detail'),
    # /group/name/subjNN/public_id/config
    url(r'^group/(?P<group_name>[\w-]+)/subj(?P<gs_id>[0-9]+)/(?P<public_id>[0-9a-f]+)/config/$',
        kviews.DeviceConfig.as_view(), name='group-subject-device-config'),
    # /public_id/upload
    url(r'^group/(?P<group_name>[\w-]+)/subj(?P<gs_id>[0-9]+)/(?P<public_id>[0-9a-f]+)/upload/$',
    views_admin.upload,
        name='group-subject-device-upload'),
    # /group/name/subjNN/converter(.ext)         Subject's data
    url(r'^group/(?P<group_name>[\w-]+)/subj(?P<gs_id>[0-9]+)/(?P<converter>\w+)\.?(?P<format>[\w-]+)?$',
        group.group_data, name='group-subject-data'),
    # /group/name/subjNN/create/                 Add subject device
    url(r'^group/(?P<group_name>[\w-]+)/subj(?P<gs_id>[0-9]+)/create/$',
        kviews.DeviceCreate.as_view(), name='group-subject-device-create'),

    # /group/name/subjNN/public_id/
    #url(r'^group/(?P<group_name>[\w-]+)/subj(?P<gs_id>[0-9]+)/(?P<public_id>[0-9a-f]+)/$',
    #    group.GroupSubjectDeviceDetail.as_view(), name='group-subject-device'),
    # /group/name/subjNN/public_id/              Subject's device detail
    #url(r'^group/(?P<group_name>[\w-]+)/subj(?P<gs_id>[0-9]+)/(?P<public_id>[0-9a-f]+)/$',
    #    group.GroupSubjectDetail.as_view(), name='group-subject-data'),

    # Funf
    url(r'^funf/config/(?P<device_id>[A-Fa-f0-9]+)?/?$', funf.config_funf,
        name='funf-journal-config'),

    # Twitter and other social sites
    url(r'^twitter/', include(twitter.urlpatterns)),
    url(r'^facebook/', include(facebook.urlpatterns)),
    url(r'^instagram/', include(instagram.urlpatterns)),

    # Main frontpage
    url(r'^$', kviews.MainView.as_view(), name='main'),
    ]

urlpatterns = [ ]
if 'data' in settings.WEB_COMPONENTS:
    urlpatterns += urls_data
if 'ui' in settings.WEB_COMPONENTS:
    urlpatterns += urls_ui
else:
    urlpatterns.append(url(r'^$', TemplateView.as_view(template_name='koota/main_data.html'), name='main'))

from kdata.devices import aware, funf, purplerobot, ios, android
from kdata.devices import facebook, instagram, twitter, actiwatch
