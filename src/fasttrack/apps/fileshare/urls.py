"""
URLConf for Django user profile management.

Recommended usage is to use a call to ``include()`` in your project's
root URLConf to include this URLConf for any URL beginning with
'/profiles/'.

"""

from django.conf.urls.defaults import *



urlpatterns = patterns('fileshare.views',
                       url(r'^$',
                           'setting',
                           name='setting'),
                       url(r'^plugins$',
                           'plugins',
                           name='plugins'),
                       url(r'^(?P<rule_id>\d+)/$',
                           'edit_setting',
                           name='edit_setting'),
                       url(r'^state/(?P<rule_id>\d+)/$',
                           'toggle_rule_state',
                           name='toggle_rule_state'),
                       url(r'^(?P<rule_id>\d+)/security/(?P<plugin_index>\d+)/$',
                           'toggle_securities_plugin',
                           name='toggle_securities_plugin'),
                       url(r'^(?P<rule_id>\d+)/validator/(?P<plugin_index>\d+)/$',
                           'toggle_validators_plugin',
                           name='toggle_validators_plugin'),
                       url(r'^(?P<rule_id>\d+)/conf/(?P<plugin_type>(security|validator))/(?P<plugin_index>\d+)/$',
                           'plugin_setting',
                           name='plugin_setting'),
                       url(r'^(?P<rule_id>\d+)/conf/(?P<plugin_type>(security|validator))/(?P<plugin_index>\d+)/(?P<action>\w+)$',
                           'plugin_action',
                           name='plugin_action'),
                       )

