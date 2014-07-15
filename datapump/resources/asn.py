""" Resource for ASN information help"""
import logging

import copy
from datapump.request_helper import RequestHelper
from lxml import etree
from StringIO import StringIO
from resources import Resource
log = logging.getLogger(__name__)


class ASN(Resource):
    def __init__(self, workspace):
        super(ASN, self).__init__(workspace)
        self._cached_resolver_info = {}
        
    
    def get_asn_resolver_info(self, asn_url):
        """
        Retrieve information regarding the ASN id from the ASN resolver serivce.
        After retrieval store it in the cached dict for later calls
        """
        from datapump.conf import settings
        
        if "http://asn.jesandco.org" not in asn_url and "http://purl.org" not in asn_url:
            return None;
        if asn_url in self._cached_resolver_info:
            return self._cached_resolver_info[asn_url]
        
        params = copy.deepcopy(settings.ASN_RESOLVER_SETTINGS['PARAMS'])
        params['id'] = asn_url
        body, url = RequestHelper().makeRequest(settings.ASN_RESOLVER_SETTINGS['URL'], **params)
        f = StringIO(body)
        
        tree = etree.parse(f)
        
        # If there is an error return None
        errors = tree.xpath("//*[local-name()='error']")
        if errors:
            return None
        
        # Try to get all the info we can from the response. If they don't exist
        # don't add them to the result
        standard_framework = tree.xpath("/ASNWebService/GetStandard/result/StandardDocument/Title[1]/text()")
        description = tree.xpath("/ASNWebService/GetStandard/result/Standard/Text[1]/text()")
        statement_notation = tree.xpath("/ASNWebService/GetStandard/result/Standard/StatementNotation[1]/text()")
        external_url = tree.xpath("/ASNWebService/GetStandard/result/Standard/ExactMatch[1]/Resource[contains(.,'http:')]/text()")

        result = {}
        if standard_framework:
            result['standard_framework']=standard_framework[0]
        if description:
            result['description']=description[0]
        if statement_notation:
            result['statement_notation']=statement_notation[0]
        if external_url:
            result['external_url']=external_url[0]
            
        # Cache it for later use
        self._cached_resolver_info[asn_url] = result
        return result