#Copyright 2014 University Corporation for Atmospheric Research (UCAR)
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

"""
Summary module which contains methods and classes for holding summary information to email
after the collection has been finished executing
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from collections import Counter
from conf import settings

log = logging.getLogger(__name__)

class CollectionSummary():
    def __init__(self, title, collection_id, collection_name):
        self.template_env = Environment(loader=FileSystemLoader(settings.TEMPLATES_PATH))
        
        self.title = title
        self.collection_id = collection_id
        self.collection_name = collection_name
        self.oai_count = 0
        self.delete_count = 0
        self.create_count = 0
        self.update_count = 0
        self.no_change_count = 0
        
        self.lr_published_count = 0
        self.lr_updated_count = 0
        self.lr_deleted_count = 0
        self.has_errors = False
        self.has_notes = False
        self.published_delete_error = False
        self.published_new_error = False
        self.published_update_error = False
        
        self.lr_slice_url = None
        self.initial_oai_request_url = None
        
        self.notes = []
        self.errors = []
        self.validation_errors = []
        
    def add_note(self, note):
        self.has_notes = True
        self.notes.append(note)
    
    def add_error(self, error):
        self.has_errors = True
        self.errors.append(error)
        
    def add_validation_error(self, error):
        self.has_errors = True
        self.validation_errors.append(error)
    
    def error_groupings(self):
        return Counter(self.errors)
    
    def note_groupings(self):
        return Counter(self.notes)
   
    def is_partial_failure(self):
        # If there were errors but some documents were published it was
        # a partial error. Since there is no rollback command for LR nor
        # if one document failing mean they will roll everything back

        if self.has_errors and  self.lr_published_count>0:
            return True
        else:
            return False
            
    def validate_summary(self):
        if self.delete_count != self.lr_deleted_count:
            self.published_delete_error = True
            self.add_validation_error("The number of deleted records does not equal how many were supposed to be deleted.")
        if self.create_count != self.lr_published_count:
            self.published_new_error = True
            self.add_validation_error("The number of created records does not equal how many were supposed to be created.")
        if self.update_count != self.lr_updated_count:
            self.published_update_error = True
            self.add_validation_error("The number of updated records does not equal how many were supposed to be updated.")
    
    
    def create_message(self):
        """ Create the message based off all variables set in object. The templating service that
        is being used is Jinja which is based off of Django's templating system. Except that it 
        ways to call methods within objects"""
        template = self.template_env.get_template('collection_summary.html')
        return template.render({'collection_summary':self})
    
    def email_summary(self):
        """ Email the summary after validating it """
        self.validate_summary()
        
        collection_name = self.collection_name
        if not collection_name:
            collection_name = "All"
        if self.is_partial_failure():
            subject = '%s Partially Failed: %s' % (self.title, collection_name)
        elif self.has_errors:
            subject = '%s Failed: %s' % (self.title, collection_name)
        elif self.has_notes:
            subject = '%s Success(with Notes): %s' % (self.title, collection_name)
        else:
            if not settings.EMAIL_SETTINGS['EMAIL_SUCCESSES']:
                return
            subject = '%s Success: %s' % (self.title, collection_name)
        
        msg = self.create_message()
        if not settings.EMAIL_SETTINGS['EMAIL_COLLECTION_SUMMARY']:
            log.info(msg)
            return
    
        email_message(msg, subject)

class PublishSummary():
    def __init__(self, title, publish_url):
        self.collection_summary_list = []
        self.title = title
        self.template_env = Environment(loader=FileSystemLoader(settings.TEMPLATES_PATH))
        self.publish_url = publish_url
        
    def add_collection_summary(self, collection_summary):
        self.collection_summary_list.append(collection_summary)

    def get_stats_dict(self):
        collection_count = 0
        successful_count = 0
        unsuccessful_count = 0
        unsuccessful_collections = []
        new_count = 0
        updated_count = 0
        deleted_count = 0
        no_changes_count = 0
        
        for collection_summary in self.collection_summary_list:
            if collection_summary.has_errors:
                unsuccessful_count+=1
                unsuccessful_collections.append(collection_summary.collection_name)
            else:
                successful_count+=1
            new_count+=collection_summary.lr_published_count
            updated_count+=collection_summary.lr_updated_count
            deleted_count+=collection_summary.lr_deleted_count
            no_changes_count+=collection_summary.no_change_count
            collection_count+=1
        return {'collection_count':collection_count,
                'successful_count':successful_count,
                'unsuccessful_count':unsuccessful_count,
                'unsuccessful_collections':unsuccessful_collections,
                'new_count':new_count,
                'updated_count':updated_count,
                'deleted_count':deleted_count,
                'no_changes_count':no_changes_count,
                'title':self.title,
                'publish_url':self.publish_url
                }
        
    def create_message(self):
        """ Create the message based off all variables set in object. The templating service that
        is being used is Jinja which is based off of Django's templating system. Except that it 
        ways to call methods within objects"""
        template = self.template_env.get_template('publish_summary.html')
        return template.render(self.get_stats_dict())
    
    def email_summary(self):
        """ Email the summary after validating it """
        # We only want the summary to go out if at least 2 collections were processed
        if len(self.collection_summary_list)<2:
            return
        
        msg = self.create_message()
        if not settings.EMAIL_SETTINGS['EMAIL_PUBLISH_SUMMARY']:
            log.info(msg)
            return
        subject = '%s Summary' % (self.title)
        
        email_message(msg, subject)

def email_exception( publish_exception, subject):
    """ Email a publish exception """
    msg = "An unexpected Exception happened before or Collections were published<br/><br/>" + publish_exception.__str__()
    email_message(msg, subject)
    
def email_message( message_as_text, subject):
    
    mail_settings = settings.EMAIL_SETTINGS
    from_email = mail_settings['FROM']
    to_email = mail_settings['SUMMARY_TO_LIST']
    
    msg = MIMEMultipart('alternative')
    
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(to_email)
    
    part1 = MIMEText(message_as_text, 'html')
    msg.attach(part1)

    if mail_settings['PORT']:
        server = smtplib.SMTP(mail_settings['EMAIL_SERVER'], mail_settings['PORT'])
    else:
        server = smtplib.SMTP(mail_settings['EMAIL_SERVER']) 
    
    # only need to use TLS for some mail servers like gmail
    if mail_settings['USE_TLS']:
        server.ehlo()
        server.starttls()
        server.ehlo()
    
    # Only login if applicable
    if mail_settings['ACCOUNT'] and mail_settings['PASSWORD']:
        server.login(mail_settings['ACCOUNT'] ,mail_settings['PASSWORD'])

    to_email = to_email
    server.sendmail(from_email, to_email, msg.as_string())
    server.close()