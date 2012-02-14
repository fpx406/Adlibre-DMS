"""
Module: MDT UI Views
Project: Adlibre DMS
Copyright: Adlibre Pty Ltd 2012
License: See LICENSE for license information
"""

from django.shortcuts import render_to_response, HttpResponseRedirect, get_object_or_404
from django.template import RequestContext, loader


def retrieve(request, step=None, template='retrieve.html'):

    context = { 'step': step, }
    return render_to_response(template, context, context_instance=RequestContext(request))


def upload(request, step=None, template='upload.html'):

    if request.REQUEST.get('step'):
        step = request.REQUEST.get('step')

    context = { 'step': step, }
    return render_to_response(template, context, context_instance=RequestContext(request))