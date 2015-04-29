""" Copyright 2012, 2013 UW Information Technology, University of Washington

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
from django.conf import settings
from django.core.cache import cache
from django.http import Http404
from django.utils.http import urlquote
from django.utils.translation import ugettext as _
import hashlib
import oauth2
import re
import simplejson as json
import types
import six

DEFAULT_CACHE_PERIOD = 300
# SPOT-1832.  Making the distance far enough that center of campus to furthest spot from the center
# can be found
DEFAULT_LOCATION_DISTANCE = '1000'
FALLBACK_LOCATION = {
    'CENTER_LATITUDE': '47.655003',
    'CENTER_LONGITUDE': '-122.306864',
    'ZOOM_LEVEL': '15',
    'DISTANCE': '1000',
}

def _server_request(url, method='GET', body=None, headers=None, request=None):
    """ Perform a request to the backend server and return the results. """
    client = None
    if request:
        client = getattr(request, 'ss_server_client', None)

    if not client:
        # Required settings for the client
        if not hasattr(settings, 'SS_WEB_SERVER_HOST'):
            raise Exception("Required setting missing: SS_WEB_SERVER_HOST")
        if not hasattr(settings, 'SS_WEB_OAUTH_KEY'):
            raise Exception("Required setting missing: SS_WEB_OAUTH_KEY")
        if not hasattr(settings, 'SS_WEB_OAUTH_SECRET'):
            raise Exception("Required setting missing: SS_WEB_OAUTH_SECRET")

        consumer = oauth2.Consumer(key=settings.SS_WEB_OAUTH_KEY, secret=settings.SS_WEB_OAUTH_SECRET)
        client = oauth2.Client(consumer)

        if request:
            request.ss_server_client = client

    if body is None:
        body = ''
    if headers is None:
        headers = {}

    if request and hasattr(request, 'user') and request.user.is_authenticated():
        # Add in the username to the request
        headers['XOAUTH_USER'] = request.user.username

    url = settings.SS_WEB_SERVER_HOST + url

    return client.request(url, method=method, body=body, headers=headers)


class SpotException(Exception):
    """ Exception for invalid requests to the backend server. """
    def __init__(self, response, message=None):
        self.response = response
        self.status_code = response.status
        if message is None:
            message = response.reason
        super(SpotException, self).__init__(message)


class SpotFavorite(object):
    """ Handle RPC for favorite data from the backend server. """
    def __init__(self, spot_id, request=None):
        self.spot_id = spot_id
        self.request = request

    def get_json(self):
        """ Get the favorite info for a user. """
        url = "/api/v1/user/me"
        if self.spot_id:
            url = url + "/favorite/{0}".format(self.spot_id)
        else:
            url = url + "/favorites"

        resp, content = _server_request(url, request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if resp.status != 200:
            raise SpotException(response=resp)

        return content if content else '{}'

    def put_json(self, body):
        """ Update the favorite data for a user. """
        url = "/api/v1/user/me/favorite/{0}".format(self.spot_id)

        resp, content = _server_request(url, method='PUT', body=body, request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if not resp.status in (200, 201):
            raise SpotException(response=resp)

        return content if content else '{}'

    def delete_json(self):
        """ Update the favorite data for a user. """
        url = "/api/v1/user/me/favorite/{0}".format(self.spot_id)

        resp, content = _server_request(url, method='DELETE', request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if resp.status != 200:
            raise SpotException(response=resp)

        return content if content else '{}'


class SpotImage(object):
    """ Handle RPC for image data from the backend server. """
    def __init__(self, spot_id, request=None):
        self.spot_id = spot_id
        self.request = request

    def _add_constrain(self, url, constrain, thumb_width, thumb_height):
        """ Add constraints to the image URL. """
        if constrain:
            constraint = []
            if thumb_width:
                constraint.append("width:%s" % thumb_width)
            if thumb_height:
                constraint.append("height:%s" % thumb_height)
            url = url + "/constrain/{0}".format(','.join(constraint))
        else:
            url = url + "/{0}x{1}".format(thumb_width, thumb_height)

        return url

    def get(self, image_id, constrain, thumb_width=None, thumb_height=None):
        """ Get a single image, possibly constrained. """
        url = "/api/v1/spot/{0}/image/{1}/thumb".format(self.spot_id, image_id)
        url = self._add_constrain(url, constrain, thumb_width, thumb_height)

        resp, content = _server_request(url, request=self.request)

        if resp.status != 200:
            raise SpotException(response=resp)

        return resp['content-type'], content

    def get_multi(self, image_ids, constrain, thumb_width=None, thumb_height=None, fill_cache=False):
        url = "/api/v1/multi_image/{0}/thumb".format(image_ids)
        url = self._add_constrain(url, constrain, thumb_width, thumb_height)

        image_cache_key = "spot_multi_image_%s" % hashlib.sha224(url).hexdigest()
        offsets_cache_key = "spot_multi_image_offsets_%s" % hashlib.sha224(url).hexdigest()

        if fill_cache:
            resp, content = _server_request(url, request=self.request)
            if resp.status != 200:
                raise SpotException(response=resp)
        
            image = content
            offsets = resp['sprite-offsets']

            cache.set(image_cache_key, image)
            cache.set(offsets_cache_key, offsets)
        else:
            image = cache.get(image_cache_key)
            offsets = cache.get(offsets_cache_key)

            if not offsets or not image:
                raise Http404

        return {
            'Content-Type': 'image/jpeg',
            'Sprite-Offsets': offsets
        }, image


class SpotPerson(object):
    """ Handle RPC for person data from the backend server. """
    def __init__(self, request=None):
        self.request = request

    def get_json(self):
        """ GET the person information. """
        url = "/api/v1/user/me"

        resp, content = _server_request(url, request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if resp.status != 200:
            raise SpotException(response=resp)

        return content

    def get(self):
        """ GET the person information. """
        data = json.loads(self.get_json())

        if not ('email' in data and data['email']):
            data['email'] = getattr(settings, 'SS_MAIL_DOMAIN', 'uw.edu')

        return data


class SpotReview(object):
    """ Handle RPC for review data from the backend server. """
    def __init__(self, spot_id, request=None):
        self.spot_id = spot_id
        self.request = request

    def get_json(self):
        """ GET the review information. """
        url = "/api/v1/spot/{0}/reviews".format(self.spot_id)

        resp, content = _server_request(url, request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if not resp.status in (200, 201):
            raise SpotException(response=resp)

        return content

    def post_json(self, body):
        """ Create a new review for a spot. """
        url = "/api/v1/spot/{0}/reviews".format(self.spot_id)

        resp, content = _server_request(url, body=body, method='POST', request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if not resp.status in (200, 201):
            raise SpotException(response=resp)

        return '{}'


class SpotShare(object):
    """ Handle RPC for share data from the backend server. """
    def __init__(self, spot_id, request=None):
        self.spot_id = spot_id
        self.request = request

    def put_json(self, body):
        """ PUT a new share request to the server. """
        url = "/api/v1/spot/{0}/share".format(self.spot_id)

        resp, content = _server_request(url, method='PUT', body=body, request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if not resp.status in (200, 201):
            raise SpotException(response=resp)

        return content

    def put(self, to_email, from_email, comment, subject):
        """ PUT a new share request to the server. """
        body = json.dumps({
            'to': to_email,
            'from': from_email,
            'comment': comment,
            'subject': subject,
        })

        return self.put_json(body)

    def put_shared_json(self, body):
        """ PUT that a share request has been viewed. """
        url = "/api/v1/spot/{0}/shared".format(self.spot_id)

        resp, content = _server_request(url, method='PUT', body=body, request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if not resp.status in (200, 201):
            raise SpotException(response=resp)

        return content

    def put_shared(self, share_hash):
        """ PUT that a share request has been viewed. """
        body = json.dumps({
            'hash': share_hash,
        })

        return self.put_shared_json(body)


class Spot(object):
    """ Handle RPC for spot data from the backend server. """
    def __init__(self, spot_id, request=None):
        self.spot_id = spot_id
        self.request = request

    @staticmethod
    def _fixup_spot(spot):
        """ Take a spot dict and pretty it up for display. """
        if 'type' in spot and isinstance(spot['type'], types.ListType):
            typeslist = []
            for t in spot["type"]:
                typeslist.append(_(t))
            spot["type"] = ', '.join(typeslist)

        spot['server_last_modified'] = spot['last_modified']
        modified_date = spot["last_modified"][5:10] + '-' + spot["last_modified"][:4]
        spot["last_modified"] = re.sub('-', '/', modified_date)

        return spot

    @staticmethod
    def _search_query(options):
        """
        Take a search options array and build a URL query string
        from it.
        """
        args = []
        for key in sorted(options):
            value = options[key]

            if isinstance(value, types.ListType):
                for item in sorted(value):
                    args.append("{0}={1}".format(urlquote(key), urlquote(item)))
            else:
                args.append("{0}={1}".format(urlquote(key), urlquote(value)))

        return '&'.join(args)

    @classmethod
    def get_all_json(self, request=None, use_cache=True, fill_cache=False, cache_period=DEFAULT_CACHE_PERIOD):
        """
        Construct and execute a search for all the spots.
        Returns the spot data.
        """
        options = {
            'limit': '0',
        }

        query = self._search_query(options)

        def _cache_key():
            return "space_search_%s" % hashlib.sha224(query).hexdigest()

        # We don't want the management command that fills the cache to get
        # a cached value
        if use_cache:
            cache_key = _cache_key()

            # The cache is (hopefully) filled from the load_open_now_cache
            # management command
            cached = cache.get(cache_key)
            if cached:
                return cached

        url = "/api/v1/spot/all?{0}".format(query)
        resp, content = _server_request(url, request=request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if resp.status == 200:
            if fill_cache:
                cache_key = _cache_key()
                cache.set(cache_key, content, cache_period)
            return content

        return '[]'

    @classmethod
    def get_all(self, request=None, use_cache=True, fill_cache=False, cache_period=DEFAULT_CACHE_PERIOD):
        """ Construct and execute a search for all the spots. """
        data = self.get_all_json(request, use_cache, fill_cache, cache_period)
        spots = json.loads(data)
        for i, spot in enumerate(spots):
            spots[i] = self._fixup_spot(spot)

        return spots

    def get_json(self):
        """ Get the spot data and return as JSON. """
        url = "/api/v1/spot/{0}".format(self.spot_id)

        resp, content = _server_request(url, request=self.request)

        if resp.status != 200:
            raise SpotException(response=resp)

        return content

    def get(self):
        spot = json.loads(self.get_json())
        spot = self._fixup_spot(spot)

        return spot

    def get_location(self, campus):
        """ Return the location information for a campus. """
        location = FALLBACK_LOCATION
        if hasattr(settings, 'SS_LOCATIONS'):
            if campus and campus in settings.SS_LOCATIONS:
                location = settings.SS_LOCATIONS[campus]
            elif hasattr(settings, 'SS_DEFAULT_LOCATION'):
                location = settings.SS_LOCATIONS[settings.SS_DEFAULT_LOCATION]

        return {
            'center_latitude': location['CENTER_LATITUDE'],
            'center_longitude': location['CENTER_LONGITUDE'],
            'zoom_level': location['ZOOM_LEVEL'],
            'distance': location.get('DISTANCE', DEFAULT_LOCATION_DISTANCE),
        }

    def get_campus_json(self, campus, use_cache=True, fill_cache=False, cache_period=DEFAULT_CACHE_PERIOD):
        """
        Construct and execute a search for the default campus level.
        Returns the spot data, and also the campus used.
        """
        location = self.get_location(campus)

        options = {
            'open_now': '1',
            'limit': '0',
        }
        options.update(location)

        query = self._search_query(options)

        def _cache_key():
            return "space_search_%s" % hashlib.sha224(query).hexdigest()

        # We don't want the management command that fills the cache to get
        # a cached value
        if use_cache:
            cache_key = _cache_key()

            # The cache is (hopefully) filled from the load_open_now_cache
            # management command
            cached = cache.get(cache_key)
            if cached:
                return cached

        url = "/api/v1/spot/?{0}".format(query)
        resp, content = _server_request(url, request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if resp.status == 200:
            if fill_cache:
                cache_key = _cache_key()
                cache.set(cache_key, content, cache_period)
            return content, location

        return '[]', location

    def get_campus(self, campus, use_cache=True, fill_cache=False, cache_period=DEFAULT_CACHE_PERIOD):
        """ Construct and execute a search for the default campus level. """
        data, location = self.get_campus_json(campus, use_cache, fill_cache, cache_period)
        spots = json.loads(data)
        for i, spot in enumerate(spots):
            spots[i] = self._fixup_spot(spot)

        return spots, location

    def search_json(self, options):
        """ Construct and execute a search request. """
        url = "/api/v1/spot/?{0}".format(self._search_query(options))

        resp, content = _server_request(url, request=self.request, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if resp.status == 200:
            return content

        return '[]'

    def search(self, options):
        """ Construct and execute a search. """
        data = json.loads(self.search_json(options))
        for i, spot in enumerate(data):
            data[i] = self._fixup_spot(spot)

        return data


def get_building_json(query=None, request=None):
    """ Get the buildings list JSON from the server app. """
    url = "/api/v1/buildings"
    if query and len(query) > 0:
        query_args = []
        for key, value in six.iteritems(query):
            query_args.append('%s=%s' % (urlquote(key), urlquote(value)))
        url = url + "?" + '&'.join(query_args)

    resp, content = _server_request(url, request=request)
    if resp.status == 200:
        return content
    else:
        return '[]'


