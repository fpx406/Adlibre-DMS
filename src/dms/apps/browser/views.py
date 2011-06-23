"""
Module: DMS Browser Django Views
Project: Adlibre DMS
Copyright: Adlibre Pty Ltd 2011
License: See LICENSE for license information
"""

import os

from plugins import models as plugin_models

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.generic.simple import direct_to_template
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.template import RequestContext, loader

from dms_plugins import models, forms
from dms.settings import DEBUG
from document_manager import DocumentManager
from browser.forms import UploadForm


def handlerError(request, httpcode, message):
    t = loader.get_template(str(httpcode)+'_custom.html')
    context = RequestContext(
        request, {'request_path': request.path,
                  'message': message, }
        )
    response = HttpResponse(t.render(context))
    response.status_code = httpcode
    return response

def index(request):
    return direct_to_template(request, 'browser/index.html')

# TODO : These should all have pagination
# TODO : These should use the WS API to browse the repository to reduce code duplication and to have pure separation.


# FIXME: Need to fix the @staff_required decorator to redirect to standard login form
# I don't think we want to necessarily use the django admin login.
def upload(request, template_name='browser/upload.html', extra_context={}):
    """
    Upload file processing. Uploaded file will be check against available rules to
    determine storage, validator, and security plugins.
    """

    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            manager = DocumentManager()
            manager.store(request, form.files['file'])
            if not manager.errors:
                messages.success(request, 'File has been uploaded.')
            else:
                messages.error(request, "; ".join(map(lambda x: x[0], manager.errors)))

    extra_context['form'] = form
    return direct_to_template(request,
                              template_name,
                              extra_context=extra_context)


def error_response(errors):
    error = errors[0]
    response = HttpResponse(error.parameter)
    response.status_code = error.code
    return response

def get_file(request, document):
    extension = request.GET.get('extension', None)
    hashcode = request.GET.get('hashcode', None)
    manager = DocumentManager()
    mimetype, filename, content = manager.get_file(request, document, hashcode, extension)
    if manager.errors:
        return error_response(manager.errors)
    response = HttpResponse(content, mimetype = mimetype)
    response["Content-Length"] = len(content)
    response['Content-Disposition'] = 'filename=%s' % filename
    return response

@staff_member_required
def revision_document(request, document):
    document_name = document
    parent_directory = request.GET.get('dir', None)
    manager = DocumentManager()
    document = manager.retrieve(request, document_name, only_metadata = True, parent_directory = parent_directory)
    extra_context = {}
    metadata = document.get_metadata()
    def get_args(fileinfo):
        args = []
        for arg in ['revision', 'hashcode']:
            if fileinfo.get(arg, None):
                args.append("%s=%s" % (arg, fileinfo[arg]))
        arg_string = ""
        if args:
            arg_string = "?" + "&".join(args)
        return arg_string
    if not manager.errors:
        if metadata:
            for fileinfo in metadata:
                fileinfo['args'] = get_args(fileinfo)
            extra_context = {
                'fileinfo_db': metadata,
                'document_name': document.get_stripped_filename(),
            }
        else:
            fileinfo = {    'revision': None, 
                            'name': document.get_filename(), 
                            'created_date': document.get_creation_time(),
                            'hashcode': document.get_hashcode(),
                            'args': get_args(fileinfo),
                        },
            extra_context = {
                'fileinfo_db': [fileinfo],
                'document_name': document.get_filename(),
            }
    else:
        messages.error(request, "; ".join(map(lambda x: x[0], manager.errors)))
    if manager.warnings:
        messages.warning(request, "; ".join(manager.warnings))
    return direct_to_template(request, 'browser/revision.html',
            extra_context=extra_context)

@staff_member_required
def files_index(request):
    mappings = models.DoccodePluginMapping.objects.all()
    extra_context = {'rules': mappings}
    return direct_to_template(request, 'browser/files_index.html',
            extra_context=extra_context)

@staff_member_required
def files_document(request, id_rule):
    mapping = get_object_or_404(models.DoccodePluginMapping, pk = id_rule)
    manager = DocumentManager()
    file_list = manager.get_file_list(mapping)
    extra_context = {
        'mapping': mapping,
        'document_list': file_list,
    }
    return direct_to_template(request, 'browser/files.html',
            extra_context = extra_context)
#settings

@staff_member_required
def plugins(request, template_name='browser/plugins.html',
            extra_context={}):
    """
    List of available plugins
    """
    manager = DocumentManager()
    plugins = manager.get_plugin_list()
    extra_context['plugin_list'] = plugins

    return direct_to_template(request, template_name, extra_context=extra_context)

@staff_member_required
def setting(request, template_name='browser/setting.html',
            extra_context={}):
    """
    Setting for adding and editing rule.
    """
    mappings = models.DoccodePluginMapping.objects.all()
    if request.method == 'POST':
        form = forms.MappingForm(request.POST)
        if form.is_valid():
            mapping = form.save()
            return HttpResponseRedirect('.')
    else:
        form = forms.MappingForm
    extra_context['form'] = form
    extra_context['rule_list'] = mappings
    return direct_to_template(request, template_name, extra_context=extra_context)


@staff_member_required
def edit_setting(request, rule_id, template_name='browser/edit_setting.html',
                   extra_context={}):
    mapping = get_object_or_404(models.DoccodePluginMapping, id=rule_id)
    form = forms.MappingForm(instance = mapping)
    if request.method == 'POST':
        form = forms.MappingForm(instance = mapping, data = request.POST)
        if form.is_valid():
            mapping = form.save()
    extra_context['rule'] = mapping
    extra_context['form'] = form
    return direct_to_template(request, template_name, extra_context=extra_context)


@staff_member_required
def toggle_rule_state(request, rule_id):
    """
    Toggle rule state of being active or disabled
    """
    mapping = get_object_or_404(models.DoccodePluginMapping, id=rule_id)
    mapping.active = not mapping.active
    mapping.save()
    return HttpResponseRedirect(reverse("setting"))

@staff_member_required
def plugin_setting(request, rule_id, plugin_id,
                   template_name='browser/plugin_setting.html',
                   extra_context={}):
    """
    Some plugins have configuration and the configuration can be different for
    each rule.
    """
    mapping = get_object_or_404(models.DoccodePluginMapping, id=rule_id)
    plugin_obj = get_object_or_404(plugin_models.Plugin, id = plugin_id)
    plugin = plugin_obj.get_plugin()
    form = plugin.get_configuration_form(mapping)
    if request.method == 'POST':
        form = plugin.get_configuration_form(mapping, data = request.POST)
        if form.is_valid():
            plugin_option = form.save()
        return HttpResponseRedirect('.')
    extra_context['form'] = form
    extra_context['rule'] = mapping
    extra_context['plugin'] = plugin
    return direct_to_template(request, template_name, extra_context=extra_context)
