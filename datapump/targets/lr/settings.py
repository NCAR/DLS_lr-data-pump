
LR_SETTINGS = {
        "PUBLISH":False,   # a good way to test. If its false it will just display the request instead of publishing it to the LR 
        "CHUNKSIZE":50,    # Chunksize to publish at a time. Using testing 50 seemed a good number without boging down the LR
        "PUBLISH_PASSWORD": None,    # The publish password that you had to setup while registering on the node you want to publish too
        "PUBLISH_URL": None,         # The publish url, ie http://node01.public.learningregistry.net
        "PUBLISH_USER": None,        # The publish user that you had to steup when registering on the node you want to publish too
        "SIGN": True,                # Whether or not to sign the document. The public node and sandbox requires it. Should stay true unless you have a reason.
        
        # The TOS attribute that is append to the envelope. Other fields can also be added like "submission_attribution"
        "TOS": {
            "submission_TOS":"http://www.learningregistry.org/information-assurances/open-information-assurances-1-0",
        },
               
        # The identity to append to the envelope
        "IDENTITY": {
                     "submitter": "a submitter", 
                     "submitter_type": "agent"
                    },
        # The id of the key you want to sign with from your system
        "KEY_ID": None,
        
        # The passprase for your key
        "PASSPHRASE": None,
        
        # At least one location where you published your public key
        "KEY_LOCATIONS": [
            None
        ],
               
        # The path to the gpg executable
        "GRG_BIN": '/bin/gpg',
        
        # This was taken from Jim's code, probably don't need it
        "GNUPG_HOME":None,
        
        # Prefix attributes that are very important to understand if your publishing as sets instead your
        # whole API at once. 
        # To distinquish a collection in a key, a PREFIX must be given so the query can be used correctly.
        # an example would be NSDL_Collection_34343243. Where NSDL_Collection is the prefix
        "COLLECTION_KEY_PREFIX":"requiredCollectionPrefix",
        
        # In order to compare what was pulled in through the OAI and whats in the LR. The identifier for
        # a record mush have a prefix so we can distinquish it in the keys. 
        "IDENTIFIER_PREFIX":"requiredIdentifierPrefix",
        
        # Wether or not the identifer prefix is already present as the id in the oai. So if the identifier is
        # oai_nsdl:3423423434 for every record. Just define that as the prefix with concat false. but
        # if the identifier in the oai is just 3423423434. you would need to set concat_prefix to True
        "CONCAT_PREFIX":False,
        
        # Any extra keys that you want globally added for every record
        "EXTRA_KEYS":()
}