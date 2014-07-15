""" Module that contains CouchWrapper that class that wraps the Couch APIs with methods that
are easier for publish targets to use """


import couch_wrapper
from summary import CollectionSummary
class Workspace():
    def __init__(self, oai_node, allow_collection_removal):
        self.resources = {}
        self.couch_wrapper = couch_wrapper.CouchWrapper()
        self.collection_summary = None
        self.oai_node = oai_node
        self.reset_collection()
        self.allow_collection_removal = allow_collection_removal
    def get_resource(self, resource_class):
        if resource_class not in self.resources:
            resource = resource_class(self)
            self.resources[resource_class]=resource
        return self.resources[resource_class]
    
    def set_collection(self, target_title, collection_id, collection_name, 
                        collection_library_format):
        self.collection_id = collection_id
        self.collection_name = collection_name
        self.collection_library_format = collection_library_format
        self.collection_summary = CollectionSummary(target_title, collection_id, collection_name)
        
    def reset_collection(self):
        self.couch_wrapper.reset_temp_workspace_dbs()
        self.collection_id = None
        self.collection_name = None
        self.collection_library_format = None
        self.collection_summary = None
        
    def clean(self):
        for resource in self.resources.values():
            resource.clean()
        self.couch_wrapper.clean()
    