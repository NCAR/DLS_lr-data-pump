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

import traceback

class PublishException(Exception):
    """ Special exception class that enables us to convert the stack trace into something that can
    be placed in an email """
    def __init__(self, context, base_exception=None):
        if base_exception:
            self.base_exception_string = self.exception_format(base_exception)
        else:
            self.base_exception_string = None
        self.context = context
        
    def __str__(self):
        if self.base_exception_string:
            return "%s<br/>%s" %(self.context, self.base_exception_string)
        else:
            return self.context
        
    def exception_format(self, e):
        """Convert an exception object into a string,
        complete with stack trace info, suitable for display.
        """
        tb = traceback.format_exc().replace('\n', '<br/>').replace(' ', '&nbsp;')
        return tb 