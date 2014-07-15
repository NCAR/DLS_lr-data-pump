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
""" Module that contains CouchWrapper that class that wraps the Couch APIs with methods that
are easier for publish targets to use """

import string, random
from conf import settings
import couchdb

class CouchWrapper():
    RESOURCE_DB_NAME = "resource"
    
    def __init__(self):
        if settings.COUCH_SERVER:
            couch = couchdb.Server(settings.COUCH_SERVER)
        else:
            couch = couchdb.Server()
        
        self._couch = couch
        oai_repos_db_name = self.create_unique_string(
                                    settings.COUCH_OAI_REPOS_DB_PREFIX)
        delete_db_name = self.create_unique_string(
                                    settings.COUCH_DELETE_DB_PREFIX)
        update_db_name = self.create_unique_string(
                                    settings.COUCH_UPDATE_DB_PREFIX)
        create_db_name = self.create_unique_string(
                                    settings.COUCH_CREATE_DB_PREFIX)
        
        self.all_tmp_db_name_list = [delete_db_name, update_db_name, 
                                     create_db_name, oai_repos_db_name]
        
        self.reset_temp_workspace_dbs()
        
        self.oai_repos_db = couch[oai_repos_db_name]
        self.delete_db = couch[delete_db_name]
        self.update_db = couch[update_db_name]
        self.create_db = couch[create_db_name]
        
    def reset_temp_workspace_dbs(self, create=True):
        """ reset method, it makes more sense to just delete them all then re-create them"""
        for temp_db_name in self.all_tmp_db_name_list:
            if temp_db_name in self._couch:
                self._couch.delete(temp_db_name)
            if create:
                self._couch.create(temp_db_name)
    
    def clean(self):
        self.reset_temp_workspace_dbs(False)
        self.remove_resource_documents()
        
    def add_to_db(self, db, doc_id, document):
        couch_doc = {}
        couch_doc['_id']  = doc_id
        couch_doc['document'] = document
        db.save(couch_doc)
            
    def add_to_delete_db(self,doc_id, document):
        self.add_to_db(self.delete_db, doc_id, document)
        
    def add_to_update_db(self, doc_id, document):
        self.add_to_db(self.update_db, doc_id, document)
    
    def add_to_oai_repos_db(self, doc_id, document):
        self.add_to_db(self.oai_repos_db, doc_id, document)
        
    def add_to_create_db(self, doc_id, document):
        self.add_to_db(self.create_db, doc_id, document)
    
    def create_unique_string(self, prefix, number=5):
        """ Creating a unique string is done just in case publishes start to use threads 
        if that happens each version of a couch table needs to be unique. This is just in 
        case that ever happens"""
        random_chars = ''.join(random.choice(
                            string.ascii_lowercase + string.digits) for x in range(number))           
        return '%s_%s' % (prefix, random_chars)
    
    def add_resource_doc(self, doc_name, doc):
        if CouchWrapper.RESOURCE_DB_NAME not in self._couch:
            self._couch.create(CouchWrapper.RESOURCE_DB_NAME)
        db = self._couch[CouchWrapper.RESOURCE_DB_NAME]
        db['_id'] = doc_name
        db['document'] = doc
    
    def get_resource_doc(self, doc_name):
        if doc_name in self._couch[CouchWrapper.RESOURCE_DB_NAME]:
            return self._couch[CouchWrapper.RESOURCE_DB_NAME][doc_name]
        else:
            return None
        
    def remove_resource_documents(self):
        if CouchWrapper.RESOURCE_DB_NAME in self._couch:
            self._couch.delete(CouchWrapper.RESOURCE_DB_NAME)
        
# Test method for cleaning out couch db, if some stuff gets added that shouldn't
# have been    
#    def delete_all_couch(self):
#        for i in self._couch:
#            if not i.startswith("_"):
#                self._couch.delete(i)