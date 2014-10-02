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

    Changes
    =================================================================

    sbutler1@illinois.edu: add support for filtering search params
        before sending to spotseeker server.
"""
from django.http import HttpResponse
import simplejson
from spacescout_web.spot import Spot, SpotException
from spacescout_web.org_filters import SearchFilterChain


def SearchView(request):

    chain = SearchFilterChain(request)

    search_args = {}

    for key in request.GET:
        if not chain.filters_key(key):
            search_args[key] = request.GET.getlist(key)

    search_args = chain.filter_args(search_args)

    json = Spot(None, request=request).search(search_args)
    json = simplejson.dumps(json)

    return HttpResponse(json, content_type='application/json')
