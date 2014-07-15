class Target(object):
    """ Base class for targets, that all targets created should extend from """
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
        
    def update_collection(self, workspace):
        pass
    
    def clean(self):
        pass
    
    def set_oai_node(self, oai_node):
        self.oai_node = oai_node
        
    def __init__(self, title='DataPump'):
        self.title = title