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