
#!!!!!!!!!!!!!!!!!!!!!!!! View conf.py for documentation of what these mean !!!!!!
# currently set for gmail
OAI_SERVER="http://nsdl.org"
OAI_PATH="/oai"
OAI_VERB = "ListRecords"

COUCH_SERVER = 'http://localhost:5984'
COUCH_USER = ''
COUCH_PASSORD = ''

EMAIL_SETTINGS = {'EMAIL_COLLECTION_SUMMARY':True,
                  'EMAIL_PUBLISH_SUMMARY':True,
                  'EMAIL_SUCCESSES':False,
                  'EMAIL_SERVER':'localhost',
                  'PORT':None,
                  'ACCOUNT':None,
                  'FROM':'',
                  'PASSWORD':None,
                  'SUMMARY_TO_LIST':[],
                  'USE_TLS':False}


#!!!!!!!!!!!!!!!!!!!!!!!! View targets/lr/settings.py for documentation of what these mean !!!!!!
LR_SETTINGS = {
        "PUBLISH":False,
        "PUBLISH_PASSWORD": "",
        "PUBLISH_URL": "",
        "PUBLISH_USER": "",
        "KEY_ID": "",
        "PASSPHRASE": "",
        "KEY_LOCATIONS": [
            
        ],
        "GRG_BIN": 'gpg',   # path to the gpg executable
        "GNUPG_HOME":None,
        "COLLECTION_KEY_PREFIX":"",
        "IDENTITY": {
                     "submitter": "Sumbit something", 
                     "submitter_type": "agent"
                    },
        "IDENTIFIER_PREFIX":None,
        
        # No reason to concat the prefix since its part of the identifier in the first place
        "CONCAT_PREFIX":False,
        
        # Extra keys to add to all records
        "EXTRA_KEYS":()
}