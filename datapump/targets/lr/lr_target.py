#Copyright 2011 SRI International
#Modifications Copyright 2014 University Corporation for Atmospheric Research (UCAR)
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

import logging
import json
import urllib2
import base64
from urllib2 import HTTPError
from lxml import etree
import time
from LRSignature.sign import Sign
from LRSignature.verify import Verify

from datapump.conf import settings
from datapump.targets import Target
from datapump.exception import PublishException
from datapump.request_helper import RequestHelper

import transforms

log = logging.getLogger(__name__)

class LRTarget(Target):
    """ Target class for publishing to the LR"""
    def __init__(self):
        super(LRTarget, self).__init__('LR Publish')
        self.request_helper = RequestHelper()
        self.target_settings = settings.LR_SETTINGS
        self.settings = settings
        # we only need to use the sign and verify tool if sign is turned on
        if settings.LR_SETTINGS['SIGN']:
            self.sign_tool = self.create_signtool()
            self.verify_tool = self.create_verifytool()
        else:
            self.sign_tool = None
            self.verify_tool = None
            
    def update_collection(self, workspace):
        """ Main method that is called by run. This starts the syncronizing and the publishing """
        
        self.workspace = workspace
        couch_wrapper = self.workspace.couch_wrapper
        try:
            # first we populate the couch create db with all records pulled back from the oai and
            # wrapping them in the envolope that LR expects
            self.populate_new_transformed_documents()
            
            # Comapre the OAI records to what is currently on the LR node, and thus
            # putting some of the documents up for delete, and update. If that is the case
            # those documents are then removed from the create document DB
            self.compare_oai_set_data()
            
            # save the number in our summary for emailing later
            self.workspace.collection_summary.create_count = len(couch_wrapper.create_db)
            
            # Now we call update LR for each db that we have sorted through
            self.update_lr(Target.CREATE, couch_wrapper.create_db)
            self.update_lr(Target.UPDATE, couch_wrapper.update_db)
            self.update_lr(Target.DELETE, couch_wrapper.delete_db)
        except PublishException, e:
            log.exception(e)
            self.workspace.collection_summary.add_error(e)
        except Exception, e:
            publish_exception = PublishException("Un-caught exception during publish.", e)
            log.error(publish_exception.__str__())
            self.workspace.collection_summary.add_error(publish_exception)
            
    def populate_new_transformed_documents(self):
        """ method extracts the OAI data via API then transforms the record into what
        it should be for the LR  """
        
        couch_wrapper = self.workspace.couch_wrapper
        collection_summary = self.workspace.collection_summary
        
        # This will need to be altered for other groups, what metadataPrefix to use and which
        # Transform to use. This part is specific to nsdl but might some parts might be salvageable
        # we only have transforms for nsdl_dc, comm_anno and comm_para. If future
        # ones are made another transform will have to be created.
        if self.workspace.collection_library_format in ['comm_para']:
            transformer = transforms.CommParadata(self.workspace)
            metadataPrefix_to_use = 'comm_para'
        elif self.workspace.collection_library_format in ['comm_anno']:
            transformer = transforms.CommAnno(self.workspace)
            metadataPrefix_to_use = 'comm_anno'
        else:
            transformer = transforms.NSDL(self.workspace)
            # Our transform is based on nsdl_dc format. So even if the native is
            # lar or oai_dc. It has a nsdl_dc conversion that we can pull
            metadataPrefix_to_use = 'nsdl_dc'
        
        oai_node = self.workspace.oai_node
        # Extra all the data and place it in oai_repos_db within in couch
        oai_node.extract_set_data(self.workspace.collection_id, metadataPrefix_to_use, 
                                       couch_wrapper)
        
        # We set the count in the summary bean for email use
        collection_summary.oai_count = len(couch_wrapper.oai_repos_db)

        # Settings intial oai request so it can be shown on the email
        collection_summary.initial_oai_request_url = \
            oai_node.fetcher.initial_oai_request_url
        
        # This is just in case the OAI returns 0, which do to errors sometimes happens. We
        # don't want to just remove all the records from the LR therefore. We throw an exception
        # to admins, which makes them add an argument to a manual call to allow the deletion of
        # all records to happen. 
        if len(couch_wrapper.oai_repos_db)==0 and not self.workspace.allow_collection_removal:
            raise PublishException('Zero records were found in in OAI response. If this is correct '
                    'you must add the ignore argument to the run statement --allow_collection_removal'
                                   , None)
        # now loop through and transform each oai record into an LR document 
        for db_record_id in couch_wrapper.oai_repos_db:
            doc = couch_wrapper.oai_repos_db[db_record_id]['document']
            
            (transformed_oai_reocrd, error_msg) = transformer.transform( 
                                                etree.fromstring(doc), db_record_id)

            if transformed_oai_reocrd and not error_msg:
                couch_wrapper.add_to_create_db(db_record_id, transformed_oai_reocrd)
            elif error_msg:
                collection_summary.add_note(error_msg)
                
    def compare_oai_set_data(self):
        """ Comapre OAI set to what is currently on the LR node. Note this assumes
        the same submitter every time. VERY important to remember this."""
        
        server = settings.LR_SETTINGS['PUBLISH_URL']
        path = '/slice'     
        
        if self.workspace.collection_id:
            params = { "any_tags": settings.LR_SETTINGS['COLLECTION_KEY_PREFIX']+self.workspace.collection_id}#maybe add in if they ever enable this again, "identity": self.lr_opts["identity"]["submitter"] }
        else:
            params = { "identity": settings.LR_SETTINGS['IDENTITY']['submitter']}
        
        try_index = 0
        
        response_dict = {}
        
        # We need to try more then one time to call the node API because it might be indexing
        # from another publish. Therefore if the document comes back wrong or its not up to date
        # wait a bit and try again
        while True:
            try:
                body, url = self.request_helper.makeRequest("%s%s" % (server, path), **params)
                # we save this initial slice into the summary so it can be included in the email
                self.workspace.collection_summary.lr_slice_url = url
                response_dict = json.loads(body)
                
                if response_dict['viewUpToDate'] == False:
                    # This happens either because the LR node is behind on indexing, I have
                    # seen sandbox take awhile and be weird with this. Nothing we can do. 
                    # Raise exception
                    raise PublishException('LR Fetch is not up to date, aborting.', None)
                else:
                    break
            except Exception, e:
                time.sleep(30)
                if try_index>10:
                    raise e
                try_index = try_index+1
                
        for document in response_dict['documents']:
            # Are filter parms are not actually unique, someone else could force
            # it to match ours, make sure it has correct signature before we 
            # compare
            if self.is_signature_valid(document):
                self.compare_document_to_oai(document)
        
        if "resumption_token" in response_dict:
            more_pages = True
        else:
            more_pages = False
            
        resumptionCount = 1   
        while (more_pages):
            try:
                resumptionCount += 1
                
                params['resumption_token']=response_dict["resumption_token"]
                
                try_index = 0
        
                response_dict = {}
                while True:
                    try:
                        body, url = self.request_helper.makeRequest("%s%s" % (server, path), **params)
                        response_dict = json.loads(body)
                        
                        if response_dict['viewUpToDate'] == False:
                            # This happens either because the LR node is behind on indexing, I have
                            # seen sandbox take awhile and be weird with this. Nothing we can do. 
                            # Raise exception
                            raise PublishException('LR Fetch is not up to date, aborting.', None)
                        else:
                            break
                    except Exception, e:
                        time.sleep(30)
                        if try_index>10:
                            raise e
                        try_index = try_index+1
                
                
                if "resumption_token" in response_dict:
                    more_pages = True
                else:
                    more_pages = False
            except Exception, e:
                raise PublishException("Problem trying to get next segment.", e)
            
            for document in response_dict['documents']:
                # Are filter parms are not actually unique, someone else could force
                # it to match ours, make sure it has correct signature before we 
                # compare
                if self.is_signature_valid(document):
                    return_value = self.compare_document_to_oai(document)
                    if not return_value:
                        # make a note so this document can be accounted for
                        note = "Document id %d couldn't be parsed correctly. ignoring" % document['doc_ID']
                        self.workspace.collection_summary.add_note(note)
                        log.info(note)
        
    def compare_document_to_oai(self, lr_document):
        """ Since records were found in the LR for this collection we need
        to figure out if we need to update or delete it. To make it syncronized
        with out data """
        
        couch_wrapper = self.workspace.couch_wrapper
        collection_summary = self.workspace.collection_summary
        
        if not lr_document or 'resource_data_description' not in lr_document:
            return False
        elif 'keys' not in lr_document['resource_data_description']:
            return False
        elif 'resource_data' not in lr_document['resource_data_description']:
            return False
        
        # Our identifier was saved as a key, retrieve it
        identifier = None
        for key in lr_document['resource_data_description']['keys']:
            if key.startswith(settings.LR_SETTINGS['IDENTIFIER_PREFIX']):
                identifier = key
        if not identifier:
            return False
        if settings.LR_SETTINGS['CONCAT_PREFIX']:
            identifier = identifier.replace(settings.LR_SETTINGS['IDENTIFIER_PREFIX'], '')

        # see if its contained in the oai db that we created earlier
        add_record = couch_wrapper.create_db.get(identifier)
        
        # For testing deletes
        #self.couch_wrapper.create_db.delete(add_record)
        #add_record = None
        
        if not add_record:
            # means that its no longer in our database, So we need to delete it from the
            # LR. Add to the delete table in couch db
            if not couch_wrapper.delete_db.get(identifier):
                couch_wrapper.add_to_delete_db( identifier, 
                                                     lr_document['resource_data_description'])
            collection_summary.delete_count+=1
        else:
            # it was found in the OAI. so now we compare it to see if it changed
            resource_data_description = lr_document['resource_data_description']
            add_document = add_record['document']
            if not self.compare_documents(resource_data_description, add_document):
                if not couch_wrapper.update_db.get(identifier):
                    # means that its different add it to the update. Making it have the same
                    # id, which is important since we are doing a replace
                    add_document['_id'] = lr_document['resource_data_description']['_id']
                    couch_wrapper.add_to_update_db(identifier, add_document)
                    collection_summary.update_count+=1
            else:
                # otherwise its the same
                collection_summary.no_change_count+=1
                
            # finally remove the record from the create db. Since its accounted for. Thus
            # the remaining elmenets in this db were not found in the LR therefore are creates
            couch_wrapper.create_db.delete(add_record)
        return True
        
    def is_signature_valid(self, document):
        """ Make sure the signature is ours"""
        
        if not document or 'resource_data_description' not in document:
            note = "Document id %d is invalid missing any kind of resource data." % document['doc_ID']
            self.workspace.collection_summary.add_note(note)
            log.info(note)
            return False 
        
        resource_data_description = document['resource_data_description']
        
        if 'identity' not in resource_data_description or 'submitter' not in resource_data_description['identity']:
            return False
        
        # submitter must be the same
        if resource_data_description['identity']['submitter']!=settings.LR_SETTINGS['IDENTITY']["submitter"]:
            return False
           
        # If payload placement is none or doc_type is tombstone means that it was already deleteed,
        if "payload_placement" not in resource_data_description or \
            document['resource_data_description']["payload_placement"]=="none" or \
            document['resource_data_description']["doc_type"]=="tombstone":
            return False

        is_valid_signature = self.verify_tool.verify(resource_data_description)
        if not is_valid_signature:
            note = "Document id %d does not have a valid signature. Ignoring." % document['doc_ID']
            self.workspace.collection_summary.add_note(note)
            log.info(note)
        return is_valid_signature
    
    def compare_documents(self, published_document, new_document):
        """ compare the LR document to the one that our data represents. This
        method may be changed if some fields are found to be not that important. and
        no reason to do an update, YOU CANNOT flat out compare the published_document to
        the new document. There are timestamps that the node sent over long with other ids
        and revisions that cannot be compared. We need to do field by field. The important
        one is the resource_data """
        resource_data_1 = published_document['resource_data']
        resource_data_2 = new_document['resource_data']
        
        tos1 = published_document['TOS']
        tos2 = new_document['TOS']

        identity1 = published_document['identity']
        identity2 = published_document['identity']
        
        keys1 = published_document['keys']
        keys2 = published_document['keys']
        
        payload_schema1 = published_document['payload_schema']
        payload_schema2 = published_document['payload_schema']
        
        resource_data_type1 = published_document['resource_data_type']
        resource_data_type2 = published_document['resource_data_type']
        
        
        return resource_data_1==resource_data_2 and tos1==tos2 and identity1==identity2 and \
                keys1==keys2 and payload_schema1==payload_schema2 and  \
                resource_data_type1==resource_data_type2


    def update_lr(self, action, db):
        '''
        Save to Learning Registry
        '''
        if len(db) == 0:
            return
        number_of_docs = 0
        doc_list = []
        repo_id_list = []
        for db_record_id in db:
            number_of_docs += 1
            
            doc = db[db_record_id]['document']
            
            # For updates and deletes the envelopes must contain and not contain
            # certain attributes, this takes care of that
            if action in [Target.DELETE, Target.UPDATE]:
                doc['replaces']=[doc['_id']]
                del doc['_id']
            if action==Target.DELETE:
                del doc['doc_ID']
                doc['payload_placement']="none"
                del doc['resource_data']
                del doc['_rev']
                
                # whether or not to delete this is still being discussed,
                # since a delete tombstones the original but creates a new one so
                # the delete can be distributed if someone is harvesting by slice and
                # date. If we delete these they will not see it.
                del doc['payload_schema']
                del doc['keys']
                
                if 'payload_schema_locator' in doc:
                    del doc['payload_schema_locator']
            
            # sign the document
            
            doc = self.sign(db_record_id, doc)
            doc_list.append(doc)
            repo_id_list.append(db_record_id)
            
            # We publish in chunks
            if number_of_docs >= settings.LR_SETTINGS['CHUNKSIZE']:
                self.publish_documents(doc_list, repo_id_list, action)
                doc_list = []
                repo_id_list = []
                number_of_docs = 0
        # finish with one more publish
        if number_of_docs!=0:
            self.publish_documents(doc_list, repo_id_list, action)
        
        return True
    
    def publish_documents(self, documents, repo_ids, action):
        """ Publish the chunked package of documents"""
        log.debug('trying to publish %s' % str(repo_ids))
        
        collection_summary = self.workspace.collection_summary
        try:
            body = { "documents":documents }
            content = json.dumps(body)
            if not settings.LR_SETTINGS['PUBLISH']:
                msg = 'Not publishing records, Publish is turned off. Displaying documents in log'
                #log.info(msg)
                #log.info(content)
                collection_summary.add_note(msg)
                return
            response = urllib2.urlopen(self.getPublishEndpoint(), data=content)
            publishStatus = json.load(response)
            if not publishStatus["OK"]:
                log.error(publishStatus["error"])
            
            nonpubcount = 0 
            for idx, result in enumerate(publishStatus["document_results"]):
                repo_id = repo_ids[idx]
                if not result["OK"]:
                    nonpubcount += 1
                    if "doc_ID" not in result:
                        result["doc_ID"] = "Unknown ID"
                    if "error" not in result:
                        result["error"] = "Unknown publishing error."
                    msg = "REPOID:{repoid} DOCID:{docid} ERROR: {msg}".format(repoid=repo_id, docid=result["doc_ID"], msg=result["error"])
                    log.error(msg)
                    collection_summary.add_error(msg)
                
             
            pubcount = len(repo_ids) - nonpubcount
            
            # keep track of how many were published just in case the LR messed something up
            if action==Target.UPDATE:
                collection_summary.lr_updated_count += pubcount
            elif action==Target.DELETE:
                collection_summary.lr_deleted_count += pubcount
            else:
                collection_summary.lr_published_count += pubcount
            log.info("Published {pub} documents ), {nonpub} documents were not published.".format(pub=pubcount, nonpub=nonpubcount))

        except HTTPError as e:
            msg = "HTTP Error encoutered:{0}  message:{1}".format(e.errno, e.strerror)
            raise PublishException(msg, e)
        except Exception:
            msg = "Unexpected error while trying to publish to node."
            raise PublishException(msg, e)
        
    def sign(self, db_record_id, doc):
        """ Sign a document """
        if doc != None and self.sign_tool != None:
            log.debug("Signing doc.")
            signed = self.sign_tool.sign(doc)
            try:
                if len(signed["digital_signature"]["signature"]) == 0:
                    msg = "Problem signing document - %d" % db_record_id
                    log.error(msg)
                    self.workspace.collection_summary.add_error(msg)
            except Exception, e:
                raise PublishException( "There's a problem with the digital_signature", e)
            return signed
        else:
            log.debug("Not signing doc.")
            return doc
    
    def getPublishEndpoint(self):
        """ Gets the correct LR publishing url """
        hdrs = {"Content-Type":"application/json; charset=utf-8"}

        try:
            if settings.LR_SETTINGS['PUBLISH_USER'] is not None and settings.LR_SETTINGS['PUBLISH_PASSWORD'] is not None:
                creds = "{u}:{p}".format(u=settings.LR_SETTINGS['PUBLISH_USER'].strip(), p=settings.LR_SETTINGS['PUBLISH_PASSWORD'].strip())
                hdrs['Authorization'] = 'Basic ' + base64.encodestring(creds)[:-1]
        except Exception, e:
            raise PublishException("There's a problem trying to create publish endpoint", e)
        return urllib2.Request("{server}/publish".format(server=settings.LR_SETTINGS['PUBLISH_URL']), headers=hdrs)

    def create_signtool(self):
        """ Create a sign tool, that uses the LRSignature Module """
        try:
            if settings.LR_SETTINGS['KEY_ID'] and settings.LR_SETTINGS['PASSPHRASE'] and settings.LR_SETTINGS['KEY_LOCATIONS']:
                
                gpg = {
                       "privateKeyID": settings.LR_SETTINGS['KEY_ID'],
                       "passphrase": settings.LR_SETTINGS['PASSPHRASE'],
                       "publicKeyLocations": settings.LR_SETTINGS['KEY_LOCATIONS']
                }
                  
                if settings.LR_SETTINGS['GRG_BIN']:
                    gpg["gpgbin"] = settings.LR_SETTINGS['GRG_BIN']
                if settings.LR_SETTINGS['GNUPG_HOME']:
                    gpg["gnupgHome"] = settings.LR_SETTINGS['GNUPG_HOME']
                return Sign.Sign_0_21(**gpg)
        except Exception, e:
            raise PublishException("Error with signing configuration.", e)
            
    def create_verifytool(self):
        """ Create a verify tool, that uses the LRSignature Module """
        try:                
            gpg = {}
            if settings.LR_SETTINGS['GRG_BIN']:
                gpg["gpgbin"] = settings.LR_SETTINGS['GRG_BIN']
            if settings.LR_SETTINGS['GNUPG_HOME']:
                gpg["gnupgHome"] = settings.LR_SETTINGS['GNUPG_HOME']
            return Verify.Verify_0_21(**gpg)
        except Exception, e:
            raise PublishException("Error with signing configuration.", e)