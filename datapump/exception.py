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