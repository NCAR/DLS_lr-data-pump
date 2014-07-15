'''
Created on Oct 25, 2011

@author: jKlo 
'''
from lxml import etree
import logging
from StringIO import StringIO
from request_helper import RequestHelper
import datetime
from urllib2 import HTTPError
from conf import settings
log = logging.getLogger(__name__)

class OAIFetchNode():
    
    def __init__(self):
        self.fetcher = Fetcher()
        
    def extract_set_data(self, set_id, metadataPrefix, couch_wrapper):
        """ Extract the set data from OAI and put it in couch db """
        try:
            for (index, recset) in enumerate(self.fetcher.fetchRecords(set_id, metadataPrefix)):
                for (idx2, rec) in enumerate(recset):
                    repo_id = rec.xpath("oai:header/oai:identifier[1]/text()", namespaces=settings.OAI_NAMESPACES)[0]
                    # Note, notice the encoding then decoding, this is due to the fact
                    # eetree.toString converts special chars into entitity references, to make
                    # sure this happens we say encode it as utf-8 then decode once it comes back
                    # out
                    couch_wrapper.add_to_oai_repos_db(repo_id, etree.tostring(
                                            rec, encoding='UTF-8').decode('utf-8'))
        except HTTPError, e:
            raise e

    def get_sets_to_publish(self, collection_set_specs):
        """ Since we do not want to create a DB dependency or an OAI harvest date
        dependency. This algorithm makes sure that that
        every collection found is ListSets is published within days_for_complete_publishing. 
        To do that we assume this will be called once a day, therefore we use the day of 
        the year for indexing home many items need to be gone through every day. 
        We actually do one extra collection because chances are collections_count / published_days 
        will have a remainder. This takes care of that"""
        
        #NCS is a custom place to house collections, this allows visibility to be set for
        # which collections to publish and which metadataprefix to use
        if settings.OAI_USE_SETS and settings.NCS_SETTINGS!=None:
            collections = self.fetcher.fetchCollectionsViaNCS(collection_set_specs)
        elif settings.OAI_USE_SETS:
            collections = self.fetcher.fetchCollections(collection_set_specs)
        else:
            # You are allowed to not use sets, this will pull back all sets
            collections = [[None, None, settings.OAI_METADATA_PREFIX]]
        
        # Note returning [[None, None]] is different then returning empty []. return empty []
        # will not publish anything. While returning [[None, None]] just will not use sets for 
        # fetching from the OAI
        return collections

                  
class Fetcher():
    def __init__(self):
        self.WAIT_DEFAULT = 120 # two minutes
        self.WAIT_MAX = 5
        self.namespaces = {
              "oai" : "http://www.openarchives.org/OAI/2.0/",
              "oai_dc" : "http://www.openarchives.org/OAI/2.0/oai_dc/",
              "dc":"http://purl.org/dc/elements/1.1/",
              "dct":"http://purl.org/dc/terms/",
              "nsdl_dc":"http://ns.nsdl.org/nsdl_dc_v1.02/",
              "ieee":"http://www.ieee.org/xsd/LOMv1p0",
              "xsi":"http://www.w3.org/2001/XMLSchema-instance"
              }
        try:
            self.namespaces.update(settings.OAI_NAMESPACES)
        except Exception, e:
            log.exception("Unable to merge specified namespaces")
            raise e
        self.request_helper = RequestHelper()
        self.initial_oai_request_url = None
        
    def fetchCollectionsViaNCS(self, collection_set_specs):
        
        body, url = self.request_helper.makeRequest(settings.NCS_SETTINGS['URL'], 
                                                    **settings.NCS_SETTINGS['PARAMS'])
        f = StringIO(body)
        tree = etree.parse(f)
        list_sets = tree.xpath("//*[local-name()='Search']/*[local-name()='results']/*[local-name()='record']/*[local-name()='metadata']/*[local-name()='record']")
        
        col_names = []
        for col in list_sets:
            spec = col.xpath("*[local-name()='collection']/*[local-name()='setSpec'][1]/text()")[0]
            name = col.xpath("*[local-name()='general']/*[local-name()='title'][1]/text()")[0]
            
            library_format_list = col.xpath("*[local-name()='collection']/*[local-name()='ingest']/*[1]/@libraryFormat")
            visibility = col.xpath("*[local-name()='collection']/*[local-name()='OAIvisibility']/text()")[0]

            append = False
            if not collection_set_specs:
                append=True
            elif spec in collection_set_specs:
                append=True
           
            # The collection must have a libarary format and visibility must be public for publishing to 
            # We do NOT publish protected collections
            if append and not library_format_list:
                log.info("Collection %s does not have a library format set. Skipping" % name)
                continue
                
            if append and (visibility != "public"):
                log.info("Collection %s visibility is not marked public skipping collection" % name)
                continue

            if append:
                library_format = library_format_list[0]
                col_names.append([ name.strip(), spec.strip(), library_format.strip()])
        return col_names

    def fetchCollections(self, collection_set_specs):
        server = settings.OAI_SERVER
        path = settings.OAI_PATH
        
        params = {
                  "verb": "ListSets"
        }
        
        body, url = self.request_helper.makeRequest("%s%s" % (server, path), **params)
        f = StringIO(body)
        tree = etree.parse(f)
        list_sets = tree.xpath("oai:ListSets/oai:set", namespaces=self.namespaces)
        
        col_names = []
        for col in list_sets:
            spec = col.xpath("oai:setSpec[1]/text()", namespaces=self.namespaces)[0]
            name = col.xpath("oai:setName[1]/text()", namespaces=self.namespaces)[0]
            
            append = False
            if not collection_set_specs:
                append=True
            elif spec in collection_set_specs:
                append=True
            if append:
                col_names.append([ name.strip(), spec.strip(), settings.OAI_METADATA_PREFIX])
        
        return col_names
    
    
    def fetchRecords(self, set_id, metadataPrefix):
        '''
        Generator to fetch all records using a resumptionToken if supplied.
        ''' 
        server = settings.OAI_SERVER
        path = settings.OAI_PATH
        verb = settings.OAI_VERB

        params = { "verb": verb, "metadataPrefix": metadataPrefix}
        if set_id:
            params["set"] = set_id
        
        tok_params = { "verb": verb }

        body, initial_oai_request_url = self.request_helper.makeRequest("%s%s" % (server, path), **params)
        
        self.initial_oai_request_url =  initial_oai_request_url
        f = StringIO(body)
        
        xmlparser = etree.XMLParser(remove_comments=True)
        tree = etree.parse(f, xmlparser)
        tokenList = tree.xpath("oai:ListRecords/oai:resumptionToken/text()", namespaces=self.namespaces)
        log.debug("FIRST RESUMPTION: "+str(tokenList))
        yield tree.xpath("oai:ListRecords/oai:record", namespaces=self.namespaces)
        resumptionCount = 1   
        while (len(tokenList) == 1):
            try:
                resumptionCount += 1
                tok_params["resumptionToken"] = tokenList[0]
                body, url = self.request_helper.makeRequest("%s%s" % (server, path), **tok_params)

                f = StringIO(body)
                tree = etree.parse(f, xmlparser)
                yield tree.xpath("oai:ListRecords/oai:record", namespaces=self.namespaces)
                tokenList = tree.xpath("oai:ListRecords/oai:resumptionToken/text()", namespaces=self.namespaces)
                log.debug("HAS RESUMPTION #{0}: {1}".format(resumptionCount, str(tokenList)))
            except Exception, e:
                tokenList = []
                log.exception("Problem trying to get next segment.")
                raise e