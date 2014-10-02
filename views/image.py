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
from django.http import HttpResponse, HttpResponseNotFound

from spacescout_web.spot import SpotImage, SpotException
from spacescout_web.middleware.unpatch_vary import unpatch_vary_headers


def ImageView(request, spot_id, image_id, thumb_width=None, thumb_height=None, constrain=False):

    try:
        image = SpotImage(spot_id, request=request)
        contenttype, img = image.get(image_id, constrain, thumb_width, thumb_height)
    except SpotException as ex:
        return HttpResponse(status=ex.status_code)
    else:
        response = HttpResponse(img, content_type=contenttype)
        # Remove some headers that don't vary for images
        unpatch_vary_headers(response, ['Cookie', 'X-Mobile', 'Accept-Language', 'User-Agent'])

        return response

def MultiImageView(request, spot_id=None, image_ids=None, thumb_width=None, thumb_height=None, constrain=False):
    try:
        image = SpotImage(spot_id, request=request)
        headers, img = image.get_multi(image_ids, constrain, thumb_width, thumb_height)
    except SpotException as ex:
        return HttpResponse(status=ex.status_code)
    else:
        response = HttpResponse(img)
        response['Content-Type'] = headers['Content-Type']
        response['Sprite-Offsets'] = headers['Sprite-Offsets']
        # Remove some headers that don't vary for images
        unpatch_vary_headers(response, ['Cookie', 'X-Mobile', 'Accept-Language', 'User-Agent'])

        return response
