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
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from spacescout_web.spot import SpotReview, SpotException
from spacescout_web.views.rest_dispatch import RESTDispatch, RESTException, JSONResponse


class ReviewsView(RESTDispatch):
    def POST(self, request, spot_id):
        if not (request.user and request.user.is_authenticated()):
            return HttpResponse("User not authorized", status=401)

        try:
            review = SpotReview(spot_id, request=request)
            content = review.post_json(request.body)
        except SpotException as ex:
            return HttpResponse('error', status=ex.status_code)
        else:
            return HttpResponse(content, content_type='application/json')

    @never_cache
    def GET(self, request, spot_id):
        try:
            review = SpotReview(spot_id, request=request)
            content = review.get_json()
        except SpotException as ex:
            return HttpResponse('error', status=ex.status_code)
        else:
            return HttpResponse(content, content_type='application/json')
