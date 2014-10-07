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
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from django.utils.translation import ugettext as _
import simplejson as json
import urllib
from django.utils.datastructures import SortedDict
from mobility.decorators import mobile_template
from django.core.exceptions import ImproperlyConfigured
import re
from spacescout_web.spot import SpotFavorite, SpotShare, Spot, SpotException, get_building_json

@mobile_template('spacescout_web/{mobile/}app.html')
def HomeView(request, template=None):
    # The preference order is cookie, config, then some static values
    # That fallback order will also apply if the cookie campus isn't in
    # settings.
    campus = None

    if hasattr(settings, "SS_LOCATIONS"):
        m = re.match(r'^/([a-z]+)/', request.path)
        if m and m.group(1) in settings.SS_LOCATIONS:
            campus = m.group(1)

        if campus is None:
            cookies = request.COOKIES
            if "default_location" in cookies:
                cookie_value = cookies["default_location"]
                # The format of the cookie is this, urlencoded:
                # lat,long,campus,zoom
                campus = urllib.unquote(cookie_value).split(',')[2]
        
                if not location in settings.SS_LOCATIONS:
                    location = None

        if campus is None:
            if hasattr(settings, 'SS_DEFAULT_LOCATION'):
                campus = settings.SS_DEFAULT_LOCATION

    spaces, template_values = get_campus_data(request, campus)

    spaces = json.dumps(spaces)

    # Default to zooming in on the UW Seattle campus if no default location is set
    if hasattr(settings, 'SS_DEFAULT_LOCATION'):
        default_location = settings.SS_DEFAULT_LOCATION
        locations = settings.SS_LOCATIONS

    if (hasattr(settings, 'SS_BUILDING_CLUSTERING_ZOOM_LEVELS') and hasattr(settings, 'SS_DISTANCE_CLUSTERING_RATIO')):
        by_building_zooms = settings.SS_BUILDING_CLUSTERING_ZOOM_LEVELS
        by_distance_ratio = settings.SS_DISTANCE_CLUSTERING_RATIO
    else:
        raise ImproperlyConfigured("You need to configure your clustering constants in settings.py or local_settings.py")

    log_shared_space_reference(request)

    buildings = json.loads(get_building_json(request=request))

    favorites_json = '[]'
    if hasattr(request, 'user') and request.user.is_authenticated():
        favorites_json = SpotFavorite(None, request=request).get_json()

    # This could probably be a template tag, but didn't seem worth it for one-time use
    #TODO: hey, actually it's probably going to be a Handlebars helper and template
    buildingdict = SortedDict()
    for building in buildings:
        try:
            if not building[0] in buildingdict.keys():  # building[0] is the first letter of the string
                buildingdict[building[0]] = []

            buildingdict[building[0]].append(building)
        except:
            pass

    params = {
        'username' : request.user.username if request.user and request.user.is_authenticated() else '',
        'center_latitude': template_values['center_latitude'],
        'center_longitude': template_values['center_longitude'],
        'zoom_level': template_values['zoom_level'],
        'locations': locations,
        'default_location': default_location,
        'by_building_zooms': by_building_zooms,
        'by_distance_ratio': by_distance_ratio,
        'buildingdict': buildingdict,
        'spaces': spaces,
        'favorites_json': favorites_json,
    }

    response = render_to_response(template, params, context_instance=RequestContext(request))
    response['Cache-Control'] = 'no-cache'
    return response


def get_campus_data(request, campus):
    # Only fetch space data if we are doing an default load; otherwise
    # the page JS will just ignore what we do here and perform its
    # own search query
    spot = Spot(None, request=request)

    if not request.COOKIES.get('spacescout_search_opts', None):
        spaces, location = spot.get_campus(campus)
    else:
        spaces, location = [], spot.get_location(campus)

    return spaces, location

def log_shared_space_reference(request):
    # log shared space references
    m = re.match(r'^/space/(\d+)/.*/([a-f0-9]{32})$', request.path)
    if m:
        try:
            share = SpotShare(m.group(1), request=request)
            share.put_shared(m.group(2))
        except:
            # best effort, ignore response
            pass
