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
from django.contrib.auth.decorators import login_required
from django.utils.http import urlquote
from spacescout_web.spot import SpotPerson
from spacescout_web.views.contact import validate_back_link
import logging


logger = logging.getLogger(__name__)


@login_required
def suggest(request, spot_id=None):
    if request.method == 'POST':
        form = SuggestForm(request.POST)

        try:
            back = request.POST['back']
            validate_back_link(back)
        except:
            back = '/'

        if form.is_valid():
            back = form.cleaned_data['back']
            name = form.cleaned_data['name']
            building = form.cleaned_data['building']
            floor = form.cleaned_data['floor']
            room_number = form.cleaned_data['room_number']
            description = form.cleaned_data['description']
            justification = form.cleaned_data['justification']
            bot_test = form.cleaned_data['email_confirmation']

            browser = request.META.get('HTTP_USER_AGENT', 'Unknown')
            subject = "[Suggestion] From %s" % (name)

            if bot_test == '':
                try:
                    user_data = SpotPerson(request=request).get()

                    netid = user_data['user']
                    sender = user_data['email']

                    email_message = "A SpaceScout user has suggested the following space.\n\
                        \nSuggested Space:\n\
                        \nFrom: {name} <{sender}>\n\
                        \nNetID: {netid}\n\
                        \nBuilding: {building}\n\
                        \nFloor: {floor}\n\
                        \nRoom number: {room_number}\n\
                        \nDescription: {description}\n\
                        \nJustification: {justification}\n\
                        \nBrowser Type: {browser}".format(
                        name=name,
                        sender=sender,
                        netid=netid,
                        building=building,
                        floor=floor,
                        room_number=room_number,
                        description=description,
                        justification=justification,
                        browser=browser,
                    )

                    if not hasattr(settings, 'FEEDBACK_EMAIL_RECIPIENT'):
                        logger.error('Missing configuration: Set FEEDBACK_EMAIL_RECIPIENT for your site')
                    send_mail(subject, email_message, sender, settings.FEEDBACK_EMAIL_RECIPIENT)
                except Exception as e:
                    logger.error('Suggest failure: %s' % (e))
                    return HttpResponseRedirect('/sorry/')


            return HttpResponseRedirect('/suggest/thankyou/?back=' + urlquote(back))
    else:
        try:
            back = request.GET['back']
            validate_back_link(back)
        except:
            back = '/'

        form = SuggestForm(initial={'back': back})

    return render_to_response('spacescout_web/suggest-form.html', {
        'form': form,
        'back': back,
        'is_mobile': (request.MOBILE == 1),
    }, context_instance=RequestContext(request))


def thank_you(request, spot_id=None):
    try:
        back = request.GET['back']
        validate_back_link(back)
    except:
        back = '/'

    return render_to_response('spacescout_web/suggest-thankyou.html', {
        'back': back,
    }, context_instance=RequestContext(request))
