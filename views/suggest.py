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
from django.http import HttpResponseRedirect
from spacescout_web.forms.suggest import SuggestForm
from django.core.mail import send_mail
from django.conf import settings
from spacescout_web.views.contact import validate_back_link


def suggest(request, spot_id=None):
    if request.method == 'POST':
        form = SuggestForm(request.POST)
        back = request.POST['back'] if 'back' in request.POST \
                and not validate_back_link(request.POST['back']) else '/'
        if form.is_valid():
            name = form.cleaned_data['name']
            netid = form.cleaned_data['netid']
            sender = form.cleaned_data['sender']
            building = form.cleaned_data['building']
            floor = form.cleaned_data['floor']
            room_number = form.cleaned_data['room_number']
            description = form.cleaned_data['description']
            justification = form.cleaned_data['justification']
            bot_test = form.cleaned_data['email_confirmation']

            browser = request.META.get('HTTP_USER_AGENT', 'Unknown')

            subject = "[Suggestion] From %s" % (name)
            email_message = "Suggested Space:\n\
                           \nFrom: %s <%s>\n\
                           \nUW NetID: %s\n\
                           \nBuilding: %s\n\
                           \nFloor: %s\n\
                           \nRoom number: %s\n\
                           \nDescription: %s\n\
                           \nJustification: %s\n\
                           \nBrowser Type = %s" % (name, sender, netid, building,
                                                   floor, room_number, description,
                                                   justification, browser)

            if bot_test == '':
                try:
                    send_mail(subject, email_message, sender, settings.FEEDBACK_EMAIL_RECIPIENT)
                except:
                    return HttpResponseRedirect('/sorry/')


            return HttpResponseRedirect('/thankyou/')
    else:
        back = request.GET['back'] if request.GET and 'back' in request.GET \
            and not validate_back_link(request.GET['back']) else '/'

        form = SuggestForm()

    return render_to_response('spacescout_web/suggest-form.html', {
        'form': form,
        'back': back,
        'is_mobile': (request.MOBILE == 1),
    }, context_instance=RequestContext(request))
