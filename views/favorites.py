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
from django.http import HttpResponse
from mobility.decorators import mobile_template
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from spacescout_web.views.contact import validate_back_link
from spacescout_web.spot import SpotFavorite, SpotException

# User's favorite spaces
@login_required
@mobile_template('spacescout_web/{mobile/}favorites.html')
def FavoritesView(request, template=None):
    try:
        back = request.GET['back']
        validate_back_link(back)
    except:
        back = '/'

    return render_to_response(template,
                              {
                                  'locations': settings.SS_LOCATIONS,
                                  'back': back
                              },
                              context_instance=RequestContext(request))


# Shim to fetch server-side user favorites
@login_required
@never_cache
def API(request, spot_id=None):
    favorite = SpotFavorite(spot_id, request=request)
    
    try:
        if request.META['REQUEST_METHOD'] == 'GET':
            content = favorite.get_json()

        elif request.META['REQUEST_METHOD'] == 'PUT':
            content = favorite.put_json(request.read())

        elif request.META['REQUEST_METHOD'] == 'DELETE':
            content = favorite.delete_json()

        else:
            return HttpResponse('Method not allowed', status=405)

    except SpotException as ex:
        return HttpResponse(ex.response.reason, status=ex.status_code)

    return HttpResponse(content, content_type='application/json')

