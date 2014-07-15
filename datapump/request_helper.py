#Copyright 2011 SRI International
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
'''
Created on Oct 20, 2011

@author: jklo
'''
from urllib import urlencode
import logging
import time
import urllib2
log = logging.getLogger(__name__)

class RequestHelper():
    def __init__(self, namespaces=None, conf=None):
        self.WAIT_DEFAULT = 120 # two minutes
        self.WAIT_MAX = 5
          
    def makeRequest(self, base_url, credentials=None, **kw):
        """Actually retrieve XML from the server.
        """
        # XXX include From header?
        headers = {
                   'User-Agent': 'Learning Registry Data Pump',
                   'Content-Type': 'text/xml; charset=utf-8'
        }
        if credentials is not None:
            headers['Authorization'] = 'Basic ' + credentials.strip()
        
        request = urllib2.Request(
            "{url}?{query}".format(url=base_url, query=urlencode(kw)), headers=headers)
        log.debug("URL Requested: %s", request.get_full_url())
        return (self.retrieveFromUrlWaiting(request), request.get_full_url())
    
    def retrieveFromUrlWaiting(self, request,
                               wait_max=None, wait_default=None):
        """Get text from URL, handling 503 Retry-After.
        """
        if not wait_max:
            wait_max = self.WAIT_MAX
        
        if not wait_default:
            wait_default = self.WAIT_DEFAULT
            
        for i in range(wait_max):
            try:
                f = urllib2.urlopen(request)
                text = f.read()
                
                f.close()
                # we successfully opened without having to wait
                break
            except urllib2.HTTPError, e:
                if e.code == 503:
                    try:
                        retryAfter = int(e.hdrs.get('Retry-After'))
                    except TypeError:
                        retryAfter = None
                    if retryAfter is None:
                        time.sleep(wait_default)
                    else:
                        time.sleep(retryAfter)
                else:
                    # reraise any other HTTP error
                    raise
        else:
            raise Exception, "Waited too often (more than %s times)" % wait_max
        return text            