lr-data-pump
==========

Overview
--------
This is a utility for extracting metadata from an OAI-PMH endpoint and publishing into a Learning Registry node.

It supports NSDL_DC -> JSON-LD, and comm_para -> lr_paradata 1.0 and a custom comm_anno transformation which probably will not be used by other
groups besides NSDL. This utility will update, add, and delete by comparing what is in the LR repository and
what is coming from the OAI provider. Because of this, you can think of this utility as a way of keeping
the OAI service the same as what is in the LR.

Historical Note
---------------
This DataPump is based off of Jim Klo's datapump (https://github.com/jimklo/LRDataPump). Many changes and additions were made to his code in
order to match our requirements but the two biggest changes that should be noted is 

1)Publishing  will not re-publish an existing document
This code figures out what is different between the OAI provider and the LR and there by adds, deletes or updates an existing LR document accordingly. 

2) NSDL_DC and OAI_DC documents are published as JSON-LD  LRMI records instead of as their native format. There are options to switch it back though
More information can be found below and in datapump/docs/nsdl_implementation.doc.


Features
--------
(Differences between https://github.com/jimklo/LRDataPump)
+ Handling of syncing a LR Node and an OAI provider
+ Optional use of setspecs via OAI to keep records published as groups
+ Email summaries when publishing to the LR. Includes errors warnings and summaries
+ Lazy settings, so different setting files can be setup for test and production environments
+ Abstraction code making it easy to create custom transformation for other data formats
+ Automatic lookup of ASN ids to their corresponding standard info for publishing


Prequisites
-----------
+ Python 2.7
+ pip, virtualenv,virtualenvwrapper. Installed by python
+ CouchDB (http://couchdb.apache.org/)


Installation and Use
--------------------

1. Checkout files from GitHub


        $ git clone git@github.com:UCAR/DLS_lr-data-pump.git


2. Install a virtualenv start it up,


        $ mkvirtualenv datapump --no-site-packages --python=python2.7
        $ workon datapump


3. Install dependencies while working in environment, you might also need a compiler and other libraries. Inspect the output and install other dependencies according to your environment


        (myenv)$ cd $datapump_directory_that_you_cloned_to
        (myenv)$ cd setup
        (myenv)setup $ pip install -r requirements.txt

4. Create public and private keys per instructions from the LR. Instructions can be found at http://docs.learningregistry.org/en/latest/start/20min.html. 
   Keep a hold of the key id, fingerprint and passphrase for later steps
   
5. Create symlink in your environment that points to the code base $datapump_directory_that_you_cloned_to/datapump

       $ cd $To your data_pump environment that you created$
       $ cd lib/python2.7/site-packages
       $ ln -s $datapump_directory_that_you_cloned_to/datapump datapump
       
   Note creating a custom setup.py file will enable you to remove this step, 

6. Create a settings file in the settings_files folder that sets your environment up. Note you may create
    many settings files as you would like. You can identify which settings file you want to be used while
    running it. Default is local_settings. The directions below is quickest way of getting started

        1. Copy file example_local_settings.py and paste it in the same folder calling it local_settings.py
        2. Properties that deal with the LR are found in targets/lr/settings.py, These are pulled in and overwritten
           in the local settings as LR_SETTINGS
           All values can be overwritten.
        2. Go through all properties and fill in the correct values. To understand what some of the LR values
           are info can be found at
            http://docs.learningregistry.org/en/latest/start/20min.html
        3. There are more properties that can be set. You can can figure out what they are by viewing file
           conf.py. These are the settings defining the environment, oai, mail server etc. Things that
           have nothing to do with the LR. 
           
   Note the pump project uses lazy settings. Therefore you can extend any settings.py file. The order for
   lazy loading is.
   
   1. Load conf.py.
   2. Load all target folders settings that are defined in conf.py. 
   3. Take the defined settings file that is set during the execution and load that overwriting any properties
      that were set before.



5. Invoke datapump:


        (myenv)$ python run.py $setOption --settings=local_settings

		$setOption can either be 
			1) a list setSpec that you want to publish ie setSpec1 setSpec2 etc...
		    2) --all this specifies to publish all sets. 
		    3) Nothing, this will not use sets at all and just do a direct pull from the OAI without
		       defining setSpecs
		    
6. * Invoke transforms without use of the datapump
	The file /data_pump_project/targets/lr/transforms can be used seperately from the datapump if you just need
	a script to transform a certain format to another format. An example would be
	
	import transforms
	from lxml import etree
	nsdl_dc_xml = "<nsdl_dc>$inner xml$</nsdl_dc>
	nsdl_dc_identifier = 123412
	
	transformer = transforms.NSDL(self.workspace)
	print transformer.transform(etree.fromstring(nsdl_dc_xml), nsdl_dc_identifier)
	
	This would display the nsdl_dc record as JSON-LD LRMI. 
	

7. Done


Appendix 1 - Notes
------------------
1) Depending on your data you might need to add some more ED_LEVEL_TO_AGE_RANGE entries into 
/data_pump_project/targets/lr/nsdl_dc_lrmi_mappings. You will get tons of errors saying ignoring values
if any come up that are not in that list.

nsdl_dc_lrmi_mappings file is meant to be edited and refined these mappings might not include all
fields that could be migrated over to LRMI.

2) The datapump publishes data that was retrieved via OAI provider. But the oai interface is completely separate from the  publishing. If one wanted to pull from another source like a database. All you really would need to do
would be to take file called oai_node and implement all the same methods and use that in lr_target instead
of oai_node. This was not implemented due to there is no standard on how the data and a way to get the
id of the record

Appendix 2  - Add Ons
---------------------
There are two optional functionalities that are somewhat built into the datapump. These are used by NSDL and can be
used by others if you set them up.

1) NCS - By default if publishing via sets from the OAI, the datapump uses the verb ListSets to gather the sets to publish. If you 
need a more flexible way to pull sets with their setSpecs you can use the NCS. Reasons for needing this might be
you only want to create a public vs private sets and only public sets are published or in NSDL's case you different sets
use different metadataprefixes. 

By default without using
the NCS the oai ListRecords will use the METADATA_PREFIX attribute in the settings. You can down load the NCS
code at http://sourceforge.net/projects/dlsciences/files/DCS_NCS%20-%20Collections%20System/. This houses
collections and attributes for the collections along with web services to fetch them. Once this is installed
you need to set the settings for it in your settings file. An example of how the settings could look would be
in conf.py underneath NCS

2) ASN Resolver - Some groups might have ASN's in there data. LR wants the actual framework of the ASN so it
can be used further down the chain. An ASN resolver can be created to figure out what framework the ASN belongs too,
the name of the standard and the external url if it has one. Once implemented the datapump will publish this instead
of the ASN id

To set this up, implement the method /resources/asn/ASN/get_asn_resolver_info.

asn.jesandco.org has some tools and rdf's that can be used to resolve them. Once its been implemented you just
need to add one line into your settings file RESOLVE_ASN = True



