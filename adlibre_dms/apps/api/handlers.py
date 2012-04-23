"""
Module: Piston API Handlers
Project: Adlibre DMS
Copyright: Adlibre Pty Ltd 2011, 2012
License: See LICENSE for license information
"""

import json
import os
import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from piston.handler import BaseHandler
from piston.utils import rc

from django.utils.decorators import method_decorator
from api.decorators.auth import logged_in_or_basicauth
from api.decorators.group_required import group_required

from document_manager import DocumentManager
from dms_plugins import models
from doc_codes.models import DocumentTypeRuleManagerInstance
from mdt_manager import MetaDataTemplateManager


log = logging.getLogger('dms.api.handlers')

AUTH_REALM = 'Adlibre DMS'

class BaseFileHandler(BaseHandler):

    def _get_info(self, request):
        revision = request.GET.get('r', None)
        hashcode = request.GET.get('h', None)
        extra = request.REQUEST
        log.debug('BaseFileHandler._get_info returned: %s : %s : %s.' % (revision, hashcode, extra))
        return revision, hashcode, extra


class FileHandler(BaseFileHandler):
    """
    CRUD Methods for documents
    """
    allowed_methods = ('GET', 'POST', 'DELETE', 'PUT')

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def create(self, request, code, suggested_format=None):
        # FIXME... code and file stream should be passed in separately!
        manager = DocumentManager()
        document = manager.store(request, request.FILES['file'])
        if len(manager.errors) > 0:
            log.error('FileHandler.create manager errors: %s' % manager.errors)
            return rc.BAD_REQUEST
        log.info('FileHandler.create request fulfilled for %s' % document.get_filename())
        return document.get_filename() # FIXME, should be rc.CREATED

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request, code, suggested_format=None):
        revision, hashcode, extra = self._get_info(request)
        manager = DocumentManager()
        try:
            mimetype, filename, content = manager.get_file(request, code, hashcode,
                    suggested_format, revision=revision)
        except Exception, e:
            log.error('FileHandler.read exception %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST
        if manager.errors:
            log.error('FileHandler.read manager errors: %s' % manager.errors)
            return rc.BAD_REQUEST # FIXME: file non existent, returns rc.BAD_REQUEST. should be reading RC code from plugin exception.
        response = HttpResponse(content, mimetype=mimetype)
        response["Content-Length"] = len(content)
        response['Content-Disposition'] = 'filename=%s' % filename
        log.info('FileHandler.read request fulfilled for code: %s, format: %s, rev %s, hash: %s.' % (code, suggested_format, revision, hashcode))
        return response

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def update(self, request, code, suggested_format=None):
        revision, hashcode, extra = self._get_info(request)
        # TODO refactor these verbs
        tag_string = request.PUT.get('tag_string', None)
        remove_tag_string = request.PUT.get('remove_tag_string', None)
        new_name = request.PUT.get('new_name', None)

        try:
            manager = DocumentManager()
            if new_name:
                document = manager.rename(request, code, new_name, suggested_format) #FIXME hashcode?
            else:
                document = manager.update(request, code, tag_string=tag_string, remove_tag_string=remove_tag_string,
                        extension=suggested_format) #FIXME hashcode missing?
            if len(manager.errors) > 0:
                log.error('FileHandler.update manager errors %s' % manager.errors)
                if settings.DEBUG:
                    raise Exception('FileHandler.update manager errors')
                else:
                    return rc.BAD_REQUEST
            log.info('FileHandler.update request fulfilled for code: %s, format: %s, rev: %s, hash: %s.' % (code, suggested_format, revision, hashcode))
            return HttpResponse(json.dumps( document.get_dict() )) # FIXME should be rc.ALL_OK
        except Exception, e: # FIXME
            log.error('FileHandler.update exception %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def delete(self, request, code, suggested_format=None):
    # FIXME, should return 404 if file not found, 400 if no docrule exists.
    #        full_filename = request.REQUEST.get('full_filename', None) # what is this?
    #        parent_directory = request.REQUEST.get('parent_directory', None) # FIXME! Used by no doccode!
        revision, hashcode, extra = self._get_info(request)
        manager = DocumentManager()
        try:
            log.debug('FileHandler.delete attempt with %s %s' % (code, revision))
            manager.delete_file(request, code, revision=revision, extension=suggested_format)
        except Exception, e:
            log.error('FileHandler.delete exception %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST
        if len(manager.errors) > 0:
            if settings.DEBUG:
                log.error('Manager Errors encountered %s' % manager.errors)
            return rc.BAD_REQUEST
        log.info('FileHandler.delete request fulfilled for code: %s, format: %s, rev: %s, hash: %s.' % (code, suggested_format, revision, hashcode))
        return rc.DELETED


class FileInfoHandler(BaseFileHandler):
    """
    Returns document metadata
    """
    allowed_methods = ('GET',)

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request, code, suggested_format=None):
        revision, hashcode, extra = self._get_info(request)
        manager = DocumentManager()
        document = manager.retrieve(request, code, hashcode=hashcode, revision=revision, only_metadata=True,
            extension=suggested_format)
        mapping = manager.get_plugin_mapping(document)
        if manager.errors:
            log.error('FileInfoHandler.read errors: %s' % manager.errors)
            if settings.DEBUG:
                raise Exception('FileInfoHandler.read manager.errors')
            else:
                return rc.BAD_REQUEST
            # FIXME This is ugly
        info = document.get_dict()
        info['document_list_url'] = reverse('ui_document_list', kwargs={'id_rule': mapping.pk})
        info['tags'] = document.get_tags()
        info['no_doccode'] = document.get_docrule().no_doccode
        log.info('FileInfoHandler.read request fulfilled for %s, ext %s, rev %s, hash %s' % (code, suggested_format, revision, hashcode))
        return HttpResponse(json.dumps(info))


class FileListHandler(BaseHandler):
    """
    Provides list of documents to facilitate browsing via document type rule id.
    """
    allowed_methods = ('GET','POST')

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request, id_rule):
        try:
            manager = DocumentManager()
            mapping = manager.get_plugin_mapping_by_kwargs(pk = id_rule)
            start = 0
            finish = None
            try:
                start = int(request.GET.get('start', 0))
                finish = request.GET.get('finish', None)
                order = request.GET.get('order', None)
                searchword = request.GET.get('q', None)
                tag = request.GET.get('tag', None)
                filter_date = request.GET.get('created_date', None)
                if finish:
                    finish = int(finish)
            except ValueError, e:
                log.error('FileListHandler.read ValueError %s' % e)
                if settings.DEBUG:
                    raise
                else:
                    pass
            file_list = manager.get_file_list(mapping, start, finish, order, searchword, tags=[tag],
                                                filter_date = filter_date)
            for item in file_list:
                ui_url = reverse('ui_document', kwargs = {'document_name': item['name']})
#                if 'directory' in item.keys():
#                    ui_url += "?parent_directory=" + item['directory']
                item.update({   'ui_url': ui_url,
                                'rule': mapping.get_name(),
                            })
            log.info('FileListHandler.read request fulfilled for start %s, finish %s, order %s, searchword %s, tag %s, filter_date %s.'
                                    % (start, finish, order, searchword, tag, filter_date))
            return file_list
        except Exception, e:
            log.error('FileListHandler.read Exception %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST


class TagsHandler(BaseHandler):
    """
    Provides list of tags for id_rule
    """
    allowed_methods = ('GET',)

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request, id_rule):
        try:
            manager = DocumentManager()
            mapping = manager.get_plugin_mapping_by_kwargs(pk=id_rule)
            tags = manager.get_all_tags(doccode=mapping.get_docrule())
            log.info('TagsHandler.read request fulfilled for rule %s' % (id_rule))
            return map(lambda x: x.name, tags)
        except Exception, e: # FIXME
            log.error('TagsHandler.read Exception %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST


class RevisionCountHandler(BaseHandler):
    """
    Returns revision count for a document
    """
    allowed_methods = ('GET','POST')

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request, document):
        document, extension = os.path.splitext(document)
        try:
            doccode = DocumentTypeRuleManagerInstance.find_for_string(document)
            if doccode:
                try:
                    mapping = models.DoccodePluginMapping.objects.get(doccode=doccode.get_id())
                except models.DoccodePluginMapping.DoesNotExist:
                    log.error('RevisionCountHandler.read DoccodePluginMapping.DoesNotExist exception raised')
                    raise
                manager = DocumentManager()
                rev_count = manager.get_revision_count(document, mapping)
                if rev_count <= 0: # document without revisions is broken FIXME: In future this is ok!
                    log.info('RevisionCountHandler.read rev_count %s.' % str(rev_count))
                    raise Exception('No document revisions')
                log.info('RevisionCountHandler.read request fulfilled for document %s, extension %s' % (document, extension))
                return rev_count
            else:
                log.error('RevisionCountHandler.read No Doccode')
                raise Exception('No Doccode')
        except Exception, e: # FIXME
            log.error('RevisionCountHandler.read Exception %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST


class RulesHandler(BaseHandler):
    """
    Returns list of all doc type rules in the system
    """
    allowed_methods = ('GET','POST')

    verbose_name = 'rule'
    verbose_name_plural = 'rules'

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request):
        manager = DocumentManager()
        mappings = manager.get_plugin_mappings()
        rules = list(map(lambda x: {
                            'doccode': x.get_docrule().get_title(),
                            'id': x.pk,
                            'ui_url': reverse('ui_document_list', kwargs = {'id_rule': x.pk})
                                }, mappings))
        log.info('RulesHandler.read request fulfilled')
        return rules


class RulesDetailHandler(BaseHandler):
    """
    Returns detailed information about a doc type rule
    """
    allowed_methods = ('GET','POST')

    fields = ['id', 'name', ('before_storage_plugins', ('name',)), 
                            ('storage_plugins', ('name',)), 
                            ('before_retrieval_plugins', ('name',)), 
                            ('before_removal_plugins', ('name',)),
                            ('database_storage_plugins', ('name',)),]

    verbose_name = 'rule'
    verbose_name_plural = 'rules'

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request, id_rule):
        manager = DocumentManager()
        try:
            mapping = manager.get_plugin_mapping_by_kwargs(pk=id_rule)
        except Exception, e: # FIXME
            log.error('RulesDetailHandler.read Exception %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST
        log.info('RulesDetailHandler.read request fulfilled for rule %s' % id_rule)
        return mapping


class PluginsHandler(BaseHandler):
    """
    Returns a list of plugins installed in the system
    """
    allowed_methods = ('GET','POST')

    verbose_name = 'plugin'
    verbose_name_plural = 'plugins'

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request):
        manager = DocumentManager()
        try:
            plugin_list = manager.get_plugin_list()
        except Exception, e: # FIXME
            log.error('PluginsHandler.read Exception %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST
        log.info('PluginsHandler.read request fulfilled')
        return plugin_list


class MetaDataTemplateHandler(BaseHandler):
    """
    Read / Create / Delete Meta Data Templates
    """
    allowed_methods = ('GET','POST', 'DELETE')

    """
    docrule_id is used for read
    mdt_id is use for delete
    """

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def create(self, request):

        if not request.user.is_authenticated():
            log.error('MetaDataTemplateHandler.create attempted with unauthenticated user.')
            return rc.FORBIDDEN

        # Catch post with no payload
        try:
            mdt = request.POST['mdt']
        except KeyError, e:
            log.error('MetaDataTemplateHandler.create attempted with no payload.')
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST

        # Catch improper MDT payload
        try:
            data = json.loads(str(mdt))
        except ValueError, e:
            log.error('MetaDataTemplateHandler.create attempted with bad json payload. %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST

        # Try and validate MDT
        manager = MetaDataTemplateManager()
        if not manager.validate_mdt(mdt):
            return rc.BAD_REQUEST

        # Store MDT
        result = manager.store(data)
        if result is False:
            log.error('MetaDataTemplateHandler.create error occurred on store.')
            return rc.BAD_REQUEST

        log.info('MetaDataTemplateHandler.create request fulfilled.')
        return result

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def read(self, request):
        if not request.user.is_authenticated():
            log.error('MetaDataTemplateHandler.read attempted with unauthenticated user.')
            return rc.FORBIDDEN

        # Catch get with no payload
        try:
            docrule_id = request.GET['docrule_id'] # FIXME: Need to standardize the arguments / nomenclature
        except KeyError, e:
            log.error('MetaDataTemplateHandler.read attempted with no payload.')
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST

        log.debug('MetaDataTemplateHandler.read underway with docrule_id %s.' % docrule_id)

        # Retrieve MDT from docrule_id
        manager = MetaDataTemplateManager()
        result = manager.get_mdts_for_docrule(docrule_id)

        log.debug('MetaDataTemplateHandler.read result: %s.' % result)

        if not result:
            log.error('MetaDataTemplateHandler.read error with docrule_id %s' % docrule_id)
            return rc.NOT_FOUND

        log.info('MetaDataTemplateHandler.read request fulfilled for docrule_id %s' % docrule_id)
        return result

    @method_decorator(logged_in_or_basicauth(AUTH_REALM))
    @method_decorator(group_required('api')) # FIXME: Should be more granular permissions
    def delete(self, request):
        if not request.user.is_authenticated():
            log.error('MetaDataTemplateHandler.delete attempted with unauthenticated user.')
            return rc.FORBIDDEN

        # Catch improper mdt_id in request
        try:
            mdt_id = request.REQUEST.get('mdt_id')
            log.info('MetaDataTemplateHandler.delete attempted with valid request %s' % mdt_id)
        except KeyError, e:
            log.error('MetaDataTemplateHandler.delete attempted with invalid request %s' % e)
            if settings.DEBUG:
                raise
            else:
                return rc.BAD_REQUEST

        # Catch mdt_id is None
        if mdt_id is None:
            return rc.BAD_REQUEST

        # Delete MDT via Manager
        manager = MetaDataTemplateManager()
        result = manager.delete_mdt(mdt_id)
        if result is True:
            log.info('MetaDataTemplateHandler.delete request fulfilled for mdt_id %s' % mdt_id)
            return rc.DELETED
        else:
            log.info('MetaDataTemplateHandler.delete request not found for mdt_id %s' % mdt_id)
            return rc.NOT_FOUND