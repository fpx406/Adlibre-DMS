"""
Module: Document Type Rules Model for Adlibre DMS
Project: Adlibre DMS
Copyright: Adlibre Pty Ltd 2012
License: See LICENSE for license information
Author: Iurii Garmash
"""

from django.db import models
import re

DOCCODE_TYPES = [
    ('1', 'Default'),
    ('2', 'Credit Card'),
    ('3', 'Book'),
]

class DocumentTypeRule(models.Model):
    """
    Main Model for Document Type Rules (Old Doccode).
    In order for an app to function Properly must contain:
    Basic model for storing "No doccode" Documents.
        - doccode_id = 1000 (or any no_doccode Id set)
        - no_doccode = True
        - active = True
        - regex = '' (no filename data)
    Maybe we need to add function to check and store this model on init.
    For now DMS requires it to be like so.
    """
    doccode_type = models.CharField(choices = DOCCODE_TYPES, max_length = 64, default = '1')
    doccode_id = models.IntegerField('Document Type Rule ID')
    sequence_last = models.IntegerField("Number of Documents", default=0)
    no_doccode = models.BooleanField(default = False)
    title = models.CharField("Document Type Rule Name", max_length=60)
    description = models.TextField("Description", blank=True)
    regex = models.CharField("Filename Regex", max_length=100, blank=True,
        help_text="""
        Regex To validate Filaname against. <br />
        E.g.: <br />
        [a-z]{5}[0-9]{3}<br />
        Will validate documents with name like 'abcde222'<br />
        """)
    split_string = models.CharField("Spliting Method", max_length=100, blank=True,
        help_text="""
        WARNING! Please assign a Split method for 'Default' doccode type!. <br />
        It is responsible for 'Folder hierarchy' of files stored.<br />
        E.g.:<br />
        Document name: 'abcde222'<br />
        Spliting method:  ['abcde', '222', 'abcde222']<br />
        Folder Files Stored: /{{ doccode_path }}/abcde/222/abcde222/<br />
        Split string: <br />
        """)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return u'DocumentTypeRule:' + unicode(self.get_title())

    def validate(self, document_name):
        """
        Validates DocumentTypeRule against available "document_name" string.
        Returns True if OK and False if not passed.
        """

        # TODO: expansion to validate document_name against "is_luhn_valid(self, cc)" for document_type:2 (credit Card)
        regex = '^' + self.regex + '$'
        if self.regex == '' and re.match(regex, document_name) and self.no_doccode:
            return True
        if not self.no_doccode and re.match(regex, document_name):
            return True
        return False

    def split(self, document_name=''):
        """
        Method to generate folder hierarchy to search for document depending on name.
        Returns spliting method List:
        Usage e.g.:
        File name:  abcde222.pdf (document_name = 'abcde222')
        Spliting method:  ['abcde', '222', 'abcde222']
        In case of document_type_rule == no_rule returns current DATE
        """
        if self.no_doccode or not document_name:
            # no Doccode spliting method
            return ['{{DATE}}']
        else:
            split_method = False
            if self.doccode_type == '1':
                # Default Storing Documents
                # Based on self.split_string
                if self.split_string:
                    #print 'Splitstring: ', self.split_string
                    split_list=self.split_string.split(',')
                    split_method = []
                    for pair in split_list:
                        s,e = pair.split(':')
                        split_method.append(document_name[int(s):int(e)])
                    split_method.append(document_name)

            if self.doccode_type == '2':
                split_method = [ document_name[0:4], document_name[5:9], document_name[10:13], document_name[14:18], document_name ]
            if self.doccode_type == '3':
                # Split document_name as per Project Gutenberg method for 'eBook number' not, eText
                # http://www.gutenberg.org/dirs/00README.TXT
                split_method = []
                for i in range(len(document_name)):
                    split_method.append(document_name[i-1:i])
                split_method.append(document_name)
            if not split_method:
                split_method=['Split_errors',] #folder name for improper doccdes!!!!!
                print 'Splitting Errors exist! [DocumentTypeRule.split()]'
            #print "Spliting method: ", split_method
            return split_method

    def is_luhn_valid(self, cc):
        """
        Method to validate Luhn algorithm based on:
        # Credit: http://en.wikipedia.org/wiki/Luhn_algorithm
        """
        num = [int(x) for x in str(cc)]
        return sum(num[::-2] + [sum(divmod(d * 2, 10)) for d in num[-2::-2]]) % 10 == 0

    def get_id(self):
        #print 'Doccode model "get_id" called.'
        return self.doccode_id

    def get_title(self):
        title = getattr(self, 'title', '')
        return title

    def get_directory_name(self):
        return str(self.get_id())

    def get_last_document_number(self):
        """
        Function to GET last document number for this Document Type Model
        """
        return self.sequence_last

    def set_last_document_number(self, number):
        """
        Function to SET last document number for this Document Type Model
        """
        self.sequence_last = int(number)
        self.save()
        return self

    def add_new_document(self):
        """
        Function increments last document number for this Document Type Model by int(1)
        """
        self.sequence_last += 1
        self.save()
        return self


class DocumentTypeRuleManager(object):
    def __init__(self):
        self.doccodes = DocumentTypeRule.objects.all()

    def find_for_string(self, string):
        res = DocumentTypeRule.objects.filter(no_doccode = True, active = True)[0]
        for doccode in self.doccodes:
            #print "%s is validated by %s: %s" % (string, doccode, doccode.validate(string))
            if doccode.validate(string):
                res = doccode
                break
        return res

    def get_docrules(self):
        return DocumentTypeRule.objects.all()

    def get_docrule_by_name(self, name):
        doccodes = self.get_docrules()
        try:
            doccode = doccodes.filter(title=name)[0]
            return doccode
        except: pass
        for doccode in doccodes:
            if doccode.get_title() == name:
                return doccode
        return None

DocumentTypeRuleManagerInstance = DocumentTypeRuleManager()