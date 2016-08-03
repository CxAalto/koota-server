# https://www.instagram.com/developer/

"""Instagram scraping support for Koota.

"""

import base64
from datetime import timedelta
import hmac
from json import dumps, loads
import os
import time
import urllib.parse

from django.conf import settings
from django.conf.urls import url, include
from django.core.urlresolvers import reverse
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.utils import timezone

import requests

from . import converter
from . import devices
from . import models
from . import permissions
from .views import save_data



import logging
logger = logging.getLogger(__name__)



INSTAGRAM_ID = settings.INSTAGRAM_KEY
INSTAGRAM_SECRET = settings.INSTAGRAM_SECRET
ig_permissions = settings.INSTAGRAM_PERMISSIONS

authorization_base_url = 'https://api.instagram.com/oauth/authorize/'
token_url = 'https://api.instagram.com/oauth/access_token'
API_BASE = 'https://api.instagram.com/v1/%s'


@devices.register_device_decorator(default=False)
class Instagram(devices.BaseDevice):
    dbmodel = models.OauthDevice
    converters = devices.BaseDevice.converters + [
                 ]
    config_instructions_template = (
        """Current state: {{device.oauthdevice.state}}.
        <ul>
          {% if device.oauthdevice.state != 'linked' %}<li>Please link this <a href="{% url 'instagram-link' public_id=device.public_id %}">here</a>.</li>{% endif %}
          {% if device.oauthdevice.state == 'linked' %}<li>If desired, you may unlink the device here: <a href="{% url 'instagram-unlink' public_id=device.public_id%}">here</a>.</li> {% endif %}
        </ul>
        """)
    @classmethod
    def create_hook(cls, instance, user):
        super(Instagram, cls).create_hook(instance, user)
        instance.state = 'unlinked'
        instance.save()



def gen_callback_uri(request, device):
    """Generate callback URI.  Must be done in two places and must be identical"""
    callback_uri = request.build_absolute_uri(reverse(done))
    #callback_uri = 'http://koota.cs.aalto.fi:8002'+reverse(done)
    return callback_uri



class InstagramAuth(requests.auth.AuthBase):
    """Requests auth for Instagram signing

    https://www.instagram.com/developer/secure-api-requests/

    Sort parameters, create '/endpoint|param1=v|param2=v' with sorted
    params and hmac-sha256.
    """
    def __init__(self, access_token=None):
        self.access_token = access_token
    def __call__(self, r):
        if r.method.upper() == 'GET':
            # Get required data
            url = urllib.parse.urlparse(r.url)
            qs = urllib.parse.parse_qsl(url.query)
            if self.access_token:
                qs += [('access_token', self.access_token)]
            qs = sorted(qs)
            # to_sign is /endpoint|a=b|c=d ...
            path = url.path.replace('/v1', '')
            to_sign = '|'.join([path,] + ['='.join((k,v)) for k,v in qs])
            #raise()
            # Make sig
            sig = hmac.new(INSTAGRAM_SECRET.encode('ascii'), to_sign.encode('ascii'), 'sha256').hexdigest()
            # reassemble the request
            qs_new = qs + [('sig', sig)]
            qs_new = urllib.parse.urlencode(qs_new)
            url_new = url._replace(query=qs_new)
            r.url = url_new.geturl()
            #import IPython ; IPython.embed()
        elif r.method.upper() == 'POST':
            # Get required data
            url = urllib.parse.urlparse(r.url)
            qs = urllib.parse.parse_qsl(r.body)
            if self.access_token:
                qs += [('access_token', self.access_token)]
            # Make sig
            to_sign = '|'.join([url.path,] + [','.join((k,v)) for k,v in qs])
            sig = hmac.new(INSTAGRAM_SECRET.encode('ascii'), to_sign.encode('ascii'), 'sha256').hexdigest()
            # reassemble body
            qs_new = qs + [('sig', sig)]
            qs_new = urllib.parse.urlencode(qs_new)
            r.body = qs_new
        else:
            raise NotImplementedError()
        return r



def link(request, public_id):
    """Step one of linking the device
    """
    device = models.OauthDevice.get_by_id(public_id)
    if not permissions.has_device_config_permission(request, device):
        raise exceptions.NoDevicePermission("No permission for device")
    # TODO: error handling
    callback_uri = gen_callback_uri(request, device)

    #s = requests.Session()
    #s.auth = InstagramAuth()
    #s.get('https://ig.com/path', params=dict(a=1, b=5))

    scope = ' '.join(ig_permissions)
    state = base64.b16encode(os.urandom(16)).lower()

    # 1: Request tokens
    params = dict(client_id=INSTAGRAM_ID,
                  redirect_uri=callback_uri,
                  response_type='code',
                  scope=scope,
                  state=state,
    )

    authorization_url = authorization_base_url+'?'+urllib.parse.urlencode(params)

    # save state
    device.request_key = state
    device.save()

    return HttpResponseRedirect(authorization_url)



def done(request):
    # TODO: handle error: error_reason=user_denied
    #                     &error=access_denied
    #                     &error_description=The+user+denied+your+request.
    if 'error' in request.GET:
        raise exceptions.BaseMessageKootaException("Error in instagram linking: %s"%request.GET, message="An error linking occured")

    #request.GET = QueryDict({'code': ['xxxxxxxx'],  'state': ['xxxxxxx']})
    code = request.GET['code']
    state = request.GET['state']

    # Get device object
    device = models.OauthDevice.objects.get(request_key=state)
    if not permissions.has_device_config_permission(request, device):
        raise exceptions.NoDevicePermission("No permission for device")
    callback_uri = gen_callback_uri(request, device)


    session = requests.Session()
    session.auth = InstagramAuth()
    r = session.post(token_url,
                    data=dict(client_id=INSTAGRAM_ID,
                              client_secret=INSTAGRAM_SECRET,
                              redirect_uri=callback_uri,
                              grant_type='authorization_code',
                              code=code))
    # {"access_token": "fb2e77d.47a0479900504cb3ab4a1f626d174d2d",
    #  "user": {
    #      "id": "1574083",
    #      "username": "snoopdogg",
    #      "full_name": "Snoop Dogg",
    #      "profile_picture": "..."
    #  }
    # }
    #import IPython ; IPython.embed()
    if r.status_code != 200:
        raise exceptions.BaseMessageKootaException('IG linking failed: %s %s'%(r.status_code, r.text),
                                                   message='Linking failed')
    data = r.json()

    access_token = data['access_token']
    device.attrs['instagram_user_id'] = data['user']['id']
    device.attrs['instagram_username'] = data['user']['username']

    # save these
    #device.resource_key = resource_owner_key
    device.resource_secret = access_token
    device.ts_linked = timezone.now()
    device.state = 'linked'
    device.save()
    return HttpResponseRedirect(reverse('device-config',
                                        kwargs=dict(public_id=device.public_id)))


def unlink(request, public_id):
    # Destroy the auth tokens
    device = models.OauthDevice.get_by_id(public_id)
    if not permissions.has_device_config_permission(request, device):
        raise exceptions.NoDevicePermission("No permission for device")
    device.state = 'unlinked'
    device.resource_secret = ''
    device.data = dumps(dict(unlinked=time.ctime()))
    device.save()
    return HttpResponseRedirect(reverse('device-config',
                                        kwargs=dict(public_id=device.public_id)))




def scrape_device(device_id, do_save_data=False):

    # Get basic parameters
    device = models.OauthDevice.get_by_id(device_id)
    # Check token expiry
    #if device.ts_refresh > timezone.now() + timedelta(seconds=60):
    #    logger.error('Instagram token expired')
    #    return()
    # Avoid scraping again if already done
    if (device.ts_last_fetch
        and (timezone.now() - device.ts_last_fetch < timedelta(hours=1))):
        pass
    device.ts_last_fetch = timezone.now()
    device.save()
    access_token = device.resource_secret

    # Create base OAuth session to use for everything
    session = requests.Session()
    session.auth = InstagramAuth(access_token)

    #def get(endpoint, params={ }):
    #    """Get an endpoint, adding"""
    #    if 'access_token' not in params:
    #        params = dict(params, access_token=access_token)
    #    r = session.get(API_BASE%endpoint,
    #                    params=params)
    #    return r

    def get_instagram(endpoint, params={}, filter_keys=lambda j: j):
        url = API_BASE%endpoint
        r = session.get(url, params=params)
        data = dict(endpoint=endpoint,
                    url=url,
                    data=r.text,
                    params=params,
                    timestamp=time.time(),
                    version=1,
                )
        if do_save_data:
            save_data(data, device_id, )
        return data


    ret = get_instagram('users/self')
    print(ret, '\n')

    ret = get_instagram('users/self/follows')
    print(ret, '\n')

    ret = get_instagram('users/self/followed-by')
    print(ret, '\n')

    #import IPython ; IPython.embed()


def scrape_all():
    devices = Instagram.dbmodel.objects.filter(type=Instagram.pyclass_name(),
                                               state='linked')
    for device in devices:
        print(device)
        scrape_device(device.device_id, True)

Instagram.scrape_one_function = scrape_device
Instagram.scrape_all_function = scrape_all




urlpatterns = [
    url(r'^link/(?P<public_id>[0-9a-f]+)$', link, name='instagram-link'),
    url(r'^unlink/(?P<public_id>[0-9a-f]+)$', unlink, name='instagram-unlink'),
    url(r'^done/$', done, name='instagram-done'),
]
