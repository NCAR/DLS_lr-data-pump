""" This is the main settings file that contains global settings(Settings for all targets) along with
the code to actually setup the setting variable for all targets """
import os
import importlib
LOG_LEVEL = 'INFO'


# tmp files for the couch files, Random characters are added to the end. Just in case this is being
# ran more then once, should not have to change these
COUCH_OAI_REPOS_DB_PREFIX = 'tmp_oai_repos'
COUCH_DELETE_DB_PREFIX = 'tmp_delete_db'
COUCH_UPDATE_DB_PREFIX = 'tmp_update_db'
COUCH_CREATE_DB_PREFIX = 'tmp_create_db'

# Where the couch server lives. By default its port 5984
COUCH_SERVER = 'http://localhost:5984'

# The couch user and password that you setup when you first installed couchDB
COUCH_USER = ''
COUCH_PASSORD = ''


PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))
TEMPLATES_PATH = os.path.join(PROJECT_PATH, 'templates')

# Email settings, if you want to recieve status and error emails for collections. This is optional
EMAIL_SETTINGS = {'EMAIL_COLLECTION_SUMMARY':False,
                  'EMAIL_PUBLISH_SUMMARY':False,
                  'EMAIL_SUCCESSES':False,
                  'EMAIL_SERVER':None,
                  'PORT':None,
                  'ACCOUNT':None,
                  'FROM':None,
                  'PASSWORD':None,
                  'SUMMARY_TO_LIST':None,
                  }

# defines the oai server for which to harvest from for publishing,
# These MUST be defined in the local settings file
OAI_SERVER=None
OAI_PATH=None
OAI_VERB = None

# This must be set, how it currently is setup, probably will just be nsdl_dc or oai_dc
# NSDL doesn't use this attribute since we use the NCS to pull the correct metadata prefix
OAI_METADATA_PREFIX = None

# if set to False not set parameter will be sent in nor will collections be seperated when publishing
# instead all records from the OAI will be pulled and the published
OAI_USE_SETS = True

# These should be good for the most part. You might have to defined some more to allow xpath to work
# on your schema
OAI_NAMESPACES = {
            "dc": "http://purl.org/dc/elements/1.1/", 
            "dct": "http://purl.org/dc/terms/", 
            "ieee": "http://www.ieee.org/xsd/LOMv1p0", 
            "nsdl_dc": "http://ns.nsdl.org/nsdl_dc_v1.02/", 
            "oai": "http://www.openarchives.org/OAI/2.0/", 
            "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/", 
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "comm_para":"http://ns.nsdl.org/ncs/comm_para",
            "comm_anno":"http://ns.nsdl.org/ncs/comm_anno"
        }

# NCS for which to pull the collections from. This is an add on that probably will not be used by
# other groups besides NSDL but can be found on source forge if so desired
NCS = None

#Example would be
#NCS_SETTINGS = {'URL':'$url to the ncs$',
#       'PARAMS':{'verb':'Search',
#                 'xmlFormat':'ncs_collect',
#                 'dcsStatus':'Done',
#                 'q':'ky:$put key here$',
#                 'n':'$put number to return$',
#                 's':'0'}
#       }

# ASN Resolver is used to convert an ASN to what its actual framework is an possibly get its url
RESOLVE_ASN = False


# Targets must be specified here or in a local settings file. Note TARGET_SETTINGS is not mandatory its
# optional, only if you want a specialized target settings file should you add it here
TARGETS = [("datapump.targets.lr.lr_target", "LRTarget")]
TARGET_SETTINGS = ["datapump.targets.lr.settings"]


""" Lazy settings object to hold all the variables once the os environement is set"""
class LazyOjbect(object):
    pass

""" Class that creates the wrapper around the lazy object to enable us to wait to load
the local settings until the program is started"""
class CustomSettings():
    ENVIRONMENT_VARIABLE = "SETTINGS_ENVIRONMENT"
    def __init__(self):
        self._wrapped = None
        
    def _setup(self, name):
        self._wrapped = LazyOjbect()
        settings_module = os.environ[CustomSettings.ENVIRONMENT_VARIABLE]
        
        # First add all the settings found in this file
        from datapump import conf
        for setting in dir(conf):
            if setting == setting.upper():
                setting_value = getattr(conf, setting)
                setattr(self._wrapped, setting, setting_value)

        # Try to fetch the settings file that was selected when the program was started
        environment_settings_mod = None
        try:
            package ="datapump.settings_files"
            path = package + "." + settings_module
            environment_settings_mod = importlib.import_module(path)
        except ImportError as e:
            raise ImportError(
                "Could not import settings '%s.%s' (Is it on sys.path? Is there an import error in the settings file?): %s"
                % (package, settings_module, e)
            )
        
        # Load target settings either from local settings that were set if they were set. Elese
        # Use the default ones listed in this module
        if hasattr(environment_settings_mod, "TARGET_SETTINGS"):
            target_setting_mods = getattr(environment_settings_mod, "TARGET_SETTINGS")
        else:
            target_setting_mods = getattr(self._wrapped, "TARGET_SETTINGS")

        # Now add all target settings
        if target_setting_mods:
            for target_settings in target_setting_mods:
                try:
                    mod = importlib.import_module(target_settings)
                except ImportError as e:
                    raise ImportError(
                        "Could not import settings '%s' (Is it on sys.path? Is there an import error in the settings file?): %s"
                        % (target_settings, e)
                    )
                
                for setting in dir(mod):
                    if setting == setting.upper():
                        setting_value = getattr(mod, setting)
                        setattr(self._wrapped, setting, setting_value)

        # Finally Override with the environment setings
        for setting in dir(environment_settings_mod):
            if setting == setting.upper():
                setting_value = getattr(environment_settings_mod, setting)
                # Dicts are overrides not overwrites
                if  hasattr(self._wrapped, setting) and \
                        type(getattr(self._wrapped, setting))==type({}) and type(setting_value)==type({}):
                    getattr(self._wrapped, setting).update(setting_value)
                else:
                    setattr(self._wrapped, setting, setting_value)

    # This is the cheat method which enables us to fetch the attributes that were set in the lazy object
    # instead of in the actual object itself
    def __getattr__(self, name):
        if self._wrapped is None:
            self._setup(name)
        return getattr(self._wrapped, name)

# Setttings variable is used throughout the pogram which wraps the lazy object
settings = CustomSettings()