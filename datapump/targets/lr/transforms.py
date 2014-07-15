from lxml import etree
from urlparse import urlparse
import logging
from dateutil.parser import parse as date_parse
from datapump.conf import settings
from datapump import xpath_helper
import nsdl_dc_lrmi_mappings
import copy
from datetime import datetime, time
from datapump.exception import PublishException
log = logging.getLogger(__name__)


""" Main class for transforming nsdl_dc, comm_anno and commpara records into LR documents
that can be used for publishing """
class Transform(object):
    resource_locator_xpath = None;
    def __init__(self, workspace):
        self.workspace = workspace
        self.identity = settings.LR_SETTINGS['IDENTITY']
        self.namespaces = settings.OAI_NAMESPACES
        self.tos = settings.LR_SETTINGS['TOS']
        
    def _unique(self, seq):
        # Not order preserving
        return list(set(seq))
        
    def get_doc_template(self, collection_name):
        """ The structure of the template that is to be used """
        doc = { 
                "doc_type": "resource_data", 
                "doc_version": "0.49.0", 
                "resource_data_type" : "metadata",
                "active" : True,
                "identity": self.identity,
                "TOS": self.tos,
                "resource_locator": None,
                "keys": [],
                "payload_placement": None,
                "payload_schema": [],
                "payload_schema_locator":None,
                "payload_locator": None,
                "resource_data": None
                }
        # This might not be true for other groups, you might want to comment this out
        if collection_name:
            doc["identity"]["curator"] = collection_name
        return doc
    
    def transform(self, record, repo_id):
        """ Main NSDL transform that is used for everything"""
        doc = self.get_doc_template(self.workspace.collection_name)
        
        if(not self.resource_locator_xpath):
            return self.cannot_transform("Xpath is not sepcified")
        
        resource_locators = record.xpath(self.resource_locator_xpath, 
                                        namespaces=self.namespaces)
        if resource_locators == None or len(resource_locators) == 0:
            return self.cannot_transform("Skipping: No resource_locator")
        
        resource_locator = resource_locators[0]
        try:
            (scheme, netloc, _, _, _, _) = urlparse(resource_locator)
            if scheme == '' or netloc == '':
                return self.cannot_trasnform("Skipping: Bad resource_locator")
        except:
            return self.cannot_transform("Not a URL: %s", resource_locator)

        self.append_keys(repo_id, resource_locator, record, doc)
        doc['resource_locator'] = resource_locator
        doc["payload_placement"] = "inline"
        
        msg = self.append_payload(repo_id, resource_locator, record, doc)
        if msg:
            return self.cannot_transform(msg)
        
        # make keys unique
        doc["keys"] = self._unique(doc["keys"])
        
        for key in doc.keys():
            if (doc[key] == None):
                del doc[key]

        # signer has a problem with encoding descendents of string type
        doc = eval(repr(doc))
        
        return (doc, None)
    
    
    def append_payload(self, repo_id, resource_locator, record, doc):
        """ Subclasses must implement this method """
        raise PublishException("Append Payload method not implemented")
    
    def append_keys(self, repo_id, resouce_locator, record, document):
        """ Default keys that are assigned to every document"""
        
        
        if settings.OAI_USE_SETS:
            collection = record.xpath("oai:header/oai:setSpec[1]/text()", namespaces=self.namespaces)[0]
            # This is used to look up the record after the fact when we want to update/delete it. 
            # Prefix is appended so we try hard as we can to only retrieve ours back
            document["keys"].append("%s%s" %(settings.LR_SETTINGS['COLLECTION_KEY_PREFIX'], collection))
        
        if settings.LR_SETTINGS['CONCAT_PREFIX']:
            identifier = settings.LR_SETTINGS["IDENTIFIER_PREFIX"]+repo_id
        else:
            identifier = repo_id
        document['keys'].append(identifier)
        document['keys'].extend(settings.LR_SETTINGS["EXTRA_KEYS"])
        document["keys"] = self._unique(document["keys"])
        
    # Micro data version is here for historical purposes. But is not used anymore. LRMI is now
    # published as json ld
    def append_microdata_lrmi_doc(self, repo_id, resource_locator, record, document, properties):
        """ Default method that is to be called by subclasses to append a lrmi
        document giving it the properties sent in. """
        
        properties['url'] = resource_locator
        properties['id'] = repo_id
        document["resource_data_type"] = "metadata"

        item = {
            "type": ["http://schema.org/CreativeWork"],
            "properties": properties
        }
        
        document["payload_schema"] = ["schema.org", "LRMI", "application/microdata+json"]
        document['resource_data'] = {'items':[item]}
    
    def append_json_ld_lrmi_doc(self, repo_id, resource_locator, record, document, properties):
        """ Default method that is to be called by subclasses to append a json-ld lrmi
        document giving it the properties sent in. """
        
        properties['url'] = resource_locator
        properties['@id'] = repo_id
        properties['@context'] = [
              {"@vocab": "http://schema.org/",
               "url": { "@type": "@id" },
               "audience": { 
                    "@id" : "audience",       
                    "@type": "@EducationalAudience" },
              },
              {
                "lrmi": "http://lrmi.net/the-specification#",
                "useRightsUrl": {
                            "@id": "lrmi:useRightsUrl",
                            "@type": "@id"
                               }
            }
        ]

        properties['@type'] = "CreativeWork"
        document["resource_data_type"] = "metadata"        
        document["payload_schema"] = ["LRMI", "JSON-LD"]
        document['resource_data'] = properties
        
    def append_lr_paradata_doc(self, repo_id, resource_locator, record, document, activity_doc_list):
        """ Default method that is to be called by subclasses to append a LR Paradata
        document giving it the properties sent in. """
        
        document["payload_schema"] = ["LR Paradata 1.0"]
        document["resource_data_type"] = "paradata"
        document['keys'].append("paradata")

        if activity_doc_list:
            if len(activity_doc_list)==1:
                document['resource_data'] = activity_doc_list[0]
            else:
                document['resource_data'] = {
                            'collection':{
                                     'totalitems':str(len(activity_doc_list)), 
                                     'items':activity_doc_list, 
                                     }
                        }
    
    def cannot_transform(self, msg):
        log.info(msg)
        return (None, msg)
    
class NSDLNative(Transform):
    """ This is not used since nsdl_dc records we want as lrmi but was kept around because
    Jim KLO at Learning registry wrote it. Just in case we decide to publish as nsdl_dc instead
    of lrmi """
    resource_locator_xpath = "oai:metadata/nsdl_dc:nsdl_dc/dc:identifier[@xsi:type='dct:URI']/text()"
    
    def append_keys(self, repo_id, resouce_locator, record, document):
        super(NSDLNative, self).append_keys(repo_id, resouce_locator, record, document)
        subject = record.xpath("oai:metadata/nsdl_dc:nsdl_dc/dc:subject/text()", namespaces=self.namespaces)
        language = record.xpath("oai:metadata/nsdl_dc:nsdl_dc/dc:language/text()", namespaces=self.namespaces)
        edLevel = record.xpath("oai:metadata/nsdl_dc:nsdl_dc/dct:educationLevel/text()", namespaces=self.namespaces)

        document["keys"].extend(map(lambda x: x.strip(), subject))
        document["keys"].extend(map(lambda x: x.strip(), edLevel))
    
    
    def append_payload(self, repo_id, resource_locator, record, document):
        schemaLocation = record.xpath("oai:metadata/nsdl_dc:nsdl_dc/@xsi:schemaLocation", 
                                      namespaces=self.namespaces)
        
        payload = record.xpath("oai:metadata/nsdl_dc:nsdl_dc", namespaces=self.namespaces)
        document["payload_schema"].append("nsdl_dc")
        document["payload_schema_locator"] = schemaLocation[0].strip()
        document["resourceData"] = etree.tostring(payload[0]).strip() 


class NSDL(NSDLNative):
    """ Class that transforms a NSDL_DC record into lrmi """
    METADATA_PREFIX = "oai:metadata/nsdl_dc:nsdl_dc"
    
    def append_payload(self, repo_id, resource_locator, record, document ):
        """ Create the properties for the LRMI document """
        properties = {}
        
        # Loop though the mappings adding them to the dict
        for dc_attribute, lrmi_equivelent in nsdl_dc_lrmi_mappings.NSDL_DC_TO_LRMI_MAPPINGS.items(): 
            value_list = record.xpath("%s/%s/text()" %(self.METADATA_PREFIX, dc_attribute), namespaces=self.namespaces)
            lrmi_value = None
            for value in value_list:
                if isinstance(lrmi_equivelent, dict):
                    lrmi_property_key = lrmi_equivelent['property']
                    try:
                        lrmi_value = lrmi_equivelent['mapping'](value, self.workspace)
                    except Exception, e:
                        self.workspace.collection_summary.add_note(str(e))
                else:
                    lrmi_value = value
                    lrmi_property_key = lrmi_equivelent
            
                if not lrmi_value:
                    continue
                
                if lrmi_property_key in properties:
                    # only append it if its unique to the list
                    if lrmi_value not in properties[lrmi_property_key]:
                        properties[lrmi_property_key].append(lrmi_value)
                else:
                    properties[lrmi_property_key] = [lrmi_value]

        # Special way of coming up with the created date, first we look at dct:created,
        # if thats not there then we try dc:date
        created_date_str = None
        value_list = record.xpath("%s/%s/text()" %(self.METADATA_PREFIX, 'dct:created'), 
                                  namespaces=self.namespaces)
        if value_list:
            created_date_str = value_list[0]
        else:
            value_list = record.xpath("%s/%s/text()" %(self.METADATA_PREFIX, 'dc:date'), 
                                      namespaces=self.namespaces)
            if value_list:
                created_date_str = value_list[0]
        
        if created_date_str:
            try:
                # Note the default date, this is used if the date is missing values
                # so if the date string is just 2004 it will use the 1,1 for month and day
                # Trying to get dateCreated into the docment as much as possible. date_parse
                # can practically figure out almost any type of date
                # We default it to a datetime that has no time so that afterwards if the 
                # time is all zeros we can remove the time asspect of it.  This little section
                # is just trying to normalize the dates as best as possible
                created_date = date_parse(created_date_str, default=datetime(2012,1,1))
                if created_date.time()==time(0,0,0):
                    created_date = created_date.date()
                properties['dateCreated'] = [created_date.isoformat()]
            except ValueError:
                log.info('Could not parse date string %s for created date. For resource %s' %(created_date_str, resource_locator ))
                self.workspace.collection_summary.add_note("Could not parse date string, not publishing created_date for record.")
        if not properties:
            return "No nsdl_dc fields to transform"
        
        self.append_json_ld_lrmi_doc(repo_id, resource_locator, record, document, properties)

    
class CommParadata(Transform):
    """ class that transforms comm_paradata into a LR Paradocument. Since this uses attributes
    we do it a different way then LRMI and use template dicts which are substuted for values. 
    anything that contains xpath will be substituted"""
    
    resource_locator_xpath = "oai:metadata/comm_para:commParadata/comm_para:usageDataResourceURL/text()"
    
    AUDIENCE_MAPPING = {"objectType":"$xpath{@audience}",
                        "description":["$xpath{@edLevel}", "$xpath{@subject}"]
                           }
    INTEGER_VERB_MAPPING = {"action":"$xpath{@type}",
                            "date":"$xpath{@dateTimeStart}/$xpath{@dateTimeEnd}"}
    
    INTEGER_MEASURE_MAPPING = {"measureType":"count",
                                "value":"$xpath{text()}"
                              }
    
    RATING_VERB_MAPPING = {"action":"rated",
                           "date":"$xpath{@dateTimeStart}/$xpath{@dateTimeEnd}",
                          }
    RATING_MEASURE_MAPPING = {"measureType":"$xpath{@type} average",
                              "value":"$xpath{text()}",
                              "scaleMin":"$xpath{@min}",
                              "scaleMax":"$xpath{@max}",
                              "sampleSize":"$xpath{@total}"}

    def append_payload(self, repo_id, resource_locator, record, document):
                
        paradata_title = record.xpath("oai:metadata/comm_para:commParadata/comm_para:paradataTitle/comm_para:string/text()", namespaces=self.namespaces)
        paradata_description = record.xpath("oai:metadata/comm_para:commParadata/comm_para:paradataDescription/comm_para:string/text()", namespaces=self.namespaces)
        usage_data_provided_for_name = record.xpath("oai:metadata/comm_para:commParadata/comm_para:usageDataProvidedForName/comm_para:string/text()", namespaces=self.namespaces)
        
        content = None
        if paradata_description:
            content = paradata_description[0]
        elif usage_data_provided_for_name:
            content = usage_data_provided_for_name[0]
        elif paradata_title:
            content = paradata_title[0]
        
        activity_list = []
        
        #Integer type, loop through all and create activities
        integer_element_list = record.xpath("oai:metadata/comm_para:commParadata/comm_para:usageDataSummary/comm_para:integer",
                                             namespaces=self.namespaces)
        for integer_element in integer_element_list:
            activity_doc = self.create_activity_document(resource_locator, content, integer_element, 
                                        CommParadata.INTEGER_VERB_MAPPING, 
                                        CommParadata.INTEGER_MEASURE_MAPPING)
            if activity_doc.keys():
                activity_list.append({'activity':activity_doc})
        
        
        #Rating type loop through all and create activities
        rating_element_list = record.xpath("oai:metadata/comm_para:commParadata/comm_para:usageDataSummary/comm_para:rating",
                                             namespaces=self.namespaces)
        for rating_element in rating_element_list:
            activity_doc = self.create_activity_document(resource_locator, content, rating_element, 
                                    CommParadata.RATING_VERB_MAPPING, 
                                    CommParadata.RATING_MEASURE_MAPPING)
            if activity_doc.keys():
                activity_list.append({'activity':activity_doc})
        
        if not activity_list:
            return "Cannot transform no activities to publish."
        
        self.append_lr_paradata_doc(repo_id, resource_locator, record, document, activity_list)


    def create_activity_document(self, resource_locator, content, element, verb_mapping, 
                                 measure_mapping):
        
        """ Helper method that creates the activity dict making sure that before it adds
        a key/value pair that the key actually exists"""
        activity = {'object':resource_locator}

        actor_dict = xpath_helper.replaceXpaths(element, 
                                     CommParadata.AUDIENCE_MAPPING,
                                     self.namespaces)
        if actor_dict.keys():
            activity['actor'] = actor_dict
        
        verb_dict = xpath_helper.replaceXpaths(element, 
                                     verb_mapping,
                                     self.namespaces)
        
        measure_dict = xpath_helper.replaceXpaths(element, 
                                     measure_mapping,
                                     self.namespaces)
        
        if measure_dict.keys():
            verb_dict['measure'] = measure_dict
        
        if verb_dict.keys():
            activity['verb'] =  verb_dict
        
        if content:
            activity['content'] = content
        return activity
    
    
class CommAnno(Transform):
    """ Class that transforms a comm_anno record into either an LRMI or LR Paradata
    document that can be published to the LR. Like the CommPara class this uses templated
    dicts to map things """
    resource_locator_xpath = "oai:metadata/comm_anno:comm_anno/comm_anno:annotatedID/text()"
    
    COMMENT_VERB_MAPPING = { "action": "commented",
                             "comment": "$xpath{text()}"}

    ACTIVITY_MAPPING = {"actor":{"objectType":"$xpath{comm_anno:contributors/comm_anno:contributor/@role}"},
                        "date":"$xpath{comm_anno:date/@created}",
                        "content":"$xpath{comm_anno:title/text()}"
                        }

    LRMI_PROPERTIES_MAPPING = {"name":"$xpath{comm_anno:title/text()}",
                        "description":"$xpath{comm_anno:text/text()}",
                        "dateCreated":"$xpath{comm_anno:date/@created}"}
    
   
    
    def append_payload(self, repo_id, resource_locator, record, document):
        """ Main method that is called by transform. If ASNStandard is found we append this
        record as a lrmi payload otherwise as a paradata payload"""
        asn_element_list = record.xpath("oai:metadata/comm_anno:comm_anno/comm_anno:ASNstandard",
                                             namespaces=self.namespaces)
        
        if asn_element_list and len(asn_element_list)>0:
            return self.append_lrmi_payload(repo_id, resource_locator, record, document)
        else:
            return self.append_lr_paradata_payload(repo_id, resource_locator, record, document)
    
    
    def append_lrmi_payload(self, repo_id, resource_locator, record, document):
        """ LRMI version of the payload """
        local_record = record.xpath("oai:metadata/comm_anno:comm_anno", namespaces=self.namespaces)[0]
        properties = xpath_helper.replaceXpaths(local_record, 
                                     CommAnno.LRMI_PROPERTIES_MAPPING,
                                     self.namespaces)
               
        asn_element_list = record.xpath("oai:metadata/comm_anno:comm_anno/comm_anno:ASNstandard",
                                             namespaces=self.namespaces)
        
        alignments = []
        # We add a educational alignment for each ASN Standard
        for asn_element in asn_element_list:
            
            alignment = nsdl_dc_lrmi_mappings.educational_alignment(asn_element.text, 
                                                     self.workspace)
            if alignment:
                alignments.append(alignment)
            
        if alignments:
            properties['educationalAlignment'] = alignments
        
        if not properties:
            return "No nsdl_dc fields to trasnsform"
        self.append_json_ld_lrmi_doc(repo_id, resource_locator, record, document, properties)
        
    def append_lr_paradata_payload(self, repo_id, resource_locator, record, document):
        """ LR Para payload version"""
        local_record = record.xpath("oai:metadata/comm_anno:comm_anno", namespaces=self.namespaces)[0]
        activity_list = []
        comment_element_list = local_record.xpath("comm_anno:text",
                                             namespaces=self.namespaces)
        activity_base_record = xpath_helper.replaceXpaths(local_record, 
                                                     CommAnno.ACTIVITY_MAPPING,
                                                     self.namespaces)
        
        # for each text element we create an activity that is a comment
        for comment_element in comment_element_list:
            activity = copy.deepcopy(activity_base_record)
            activity['object'] = resource_locator
            
            verb = xpath_helper.replaceXpaths(comment_element, 
                                       CommAnno.COMMENT_VERB_MAPPING, 
                                       self.namespaces)
            activity['verb'] = verb

            if activity and activity.keys():
                activity_list.append({'activity':activity})
        if not activity_list:
            return "Cannot transform no activities to publish."
        self.append_lr_paradata_doc(repo_id, resource_locator, record, document, activity_list)