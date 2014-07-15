import logging
log = logging.getLogger(__name__)
from datapump.conf import settings
from datapump.resources.asn import ASN
""" Mappings for publishing from our nsdl_dc to LRMI """

ED_LEVEL_TO_AGE_RANGE = {
      'Pre-Kindergarten':'5-',
      'Elementary School':'6-11',
      'Early Elementary':'6-8',
      'Kindergarten':'5',
      'Grade 1':'6',
      'Grade 2':'7',
      'Upper Elementary':'8-11',
      'Grade 3':'8',
      'Grade 4':'9',
      'Grade 5':'10',
      'Middle School':'11-13',
      'Grade 6':'11',
      'Grade 7':'12',
      'Grade 8':'13',
      'High School':'14-18',
      'Grade 9':'14-15',
      'Grade 10':'15-16',
      'Grade 11':'16-17',
      'Grade 12':'17-18',
      'Higher Education':'18+',
      'Undergraduate (Lower Division)':'19+', 
      'Grade 13':'18+',
      'Grade 14':'18+',
      'Undergraduate (Upper Division)':'18+',
      'Grade 15':'18+',
      'Grade 16':'18+',
      'Technical Education (Lower Division)':'18+',
      'Technical Education (Upper Division)':'18+',
      'Graduate/Professional':'21+',
      'Graduate':'21+',
      'Informal Education':'16+',
      'Elementary School Programming':'6-11',
      'Middle School Programming':'11-13',
      'High School Programming':'14-18',
      'General Public':'16+',
      'Youth Public':'1-15',
      'Vocational/Professional Development Education':'21+',
}

def age_range(value, workspace):
    if value in ED_LEVEL_TO_AGE_RANGE:
        return ED_LEVEL_TO_AGE_RANGE[value]
    else:
        msg = 'Mapping for %s does not exist in ED_LEVEL_TO_AGE_RANGE, please add. Ignoring value.' % value
        log.error(msg)
        raise Exception(msg)

def educational_alignment(value, workspace):
    """ Transform a conformsTo object into a dict for publishing"""
    if "http://asn.jesandco.org" in value or "http://purl.org" in value:
        # for ASN we use a custom method
        return asn_educational_alignment(value, workspace)
    elif "http://" in value:
        # For others we just make the dict contain the targetUrl
        result = {'targetUrl':value, '@type': 'AlignmentObject'}
        # by default we know that if the url is project2061 we know its AAAS
        # Lets just it add it
        if "project2061" in value:
            result['educationalFramework']= \
                'American Association for the Advancement of Science'
        return result
    else:
        # Not sure what the point of returning anything else would be since there is no
        # basis what the framework is or no way to get to it
        return None

def asn_educational_alignment(asn_id, workspace):
    """ Custom asn id for conforms to transformer """
    
    if not settings.RESOLVE_ASN:
        return
    
    asn_resource = workspace.get_resource(ASN)
    asn_info = asn_resource.get_asn_resolver_info(asn_id)

    alignment = {'targetUrl':[asn_id]}

    # Note we add all these elements are arrays since the examples we saw from
    # Jim used arrays
    if asn_info:
        if 'standard_framework' in asn_info:
            alignment['educationalFramework'] = [asn_info['standard_framework']]
        if 'description' in asn_info:
            alignment['targetDescription'] = [asn_info['description']]
        if 'statement_notation' in asn_info:
            alignment['targetName'] = [asn_info['statement_notation']]
        # If it has an external URL add that to target URL, that way both 
        # the asn url can be indexed as well as the url to its corresponding framework
        if 'external_url' in asn_info:
            alignment['targetUrl'].append(asn_info['external_url'])
    else:
        # All asn's should be found if not something is a bit off, add it as a note
        msg = 'Could not retrieve ASN %s from the ASN resolver.' % asn_id
        log.info(msg)
        raise Exception(msg)
    return alignment

def copyrightHolder(value, workspace):
    if "http://" in value or "www" in value:
        return {'url':value}
    else:
        return {'name':value}

def name_value_mapping(value, workspace):
    return {'name':value}

def educationalRole(value, workspace):
    return {'educationalRole':value, '@type': '@EducationalAudience'}

# Mappings are xpaths to lrmi equivelent. Where the equivelent can be just a name or a 
# mappings if its more complex
# Note the mapping for dct:created and dc:date are found in transform since it requires more logic
NSDL_DC_TO_LRMI_MAPPINGS = {'dc:title':'name',
                            'dc:subject':'about',
                            'dct:subject':'about',
                            'dc:creator':{ 'property':'author', 'mapping':name_value_mapping},
                            'dc:language':'inLanguage',
                            'dc:type':'learningResourceType',
                            'dct:audience':{ 'property':'audience', 'mapping':educationalRole}, 
                            'dct:conformsTo':{'property':'educationalAlignment', 'mapping':educational_alignment },
                            'dc:description':'description',
                            'dc:contributor':{'property':'contributor', 'mapping':name_value_mapping },
                            'dct:coverage':{'property':'contentLocation', 'mapping':name_value_mapping},
                            'dc:source':'isBasedOnURL',
                            'dc:publisher':{'property':'publisher', 'mapping':name_value_mapping},
                            'ieee:interactivityType':'interactivityType',
                            'dct:instructionalMethod':'educationalUse',
                            'ieee:typicalLearningTime':'timeRequired',
                            'dct:educationLevel':{'property':'typicalAgeRange', 'mapping':age_range},
                            "dct:rightsHolder[@xsi:type='dct:URI']": {'property':'copyrightHolder', 'mapping':copyrightHolder},
                            "dc:rights[@xsi:type='dct:URI']": 'useRightsURL',
                            "dct:license[@xsi:type='dct:URI']": 'useRightsURL',
                            "dc:format":{'property':'encodings', 'mapping':name_value_mapping} ,
                            "dct:issued":'datePublished',
                            }
