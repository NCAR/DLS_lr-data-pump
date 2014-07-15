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

""" Module for helping with xpaths """
import re

def replaceXpaths(element, value, namespaces):
    """ Helper method that takes and element and a value(which can be an
    object or just a tring. And goes through it replacing anything that contains
    an xpath with its actual value """
    if type(value)==type({}):
        new_dict = {}
        for key, item  in value.items():
            item = replaceXpaths(element, item, namespaces)
            if item:
                new_dict[key] = item
        return new_dict
    elif (type(value)==type([])):
        new_list = []
        for item in value:
            item = replaceXpaths(element, item, namespaces)
            if item:
                new_list.append(item)
        return new_list
    elif isinstance(value, basestring):
        xpath_groupings = re.findall("(\$xpath\{(.*?)\})", value)
        new_value = value
        for xpath_group in xpath_groupings:
            xpath_values = element.xpath(xpath_group[1], namespaces=namespaces)
            if xpath_values:
                xpath_value=xpath_values[0]
            else:
                xpath_value = ""
            new_value = new_value.replace(xpath_group[0], xpath_value)

        return new_value
    else:
        return value