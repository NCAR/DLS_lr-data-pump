from __future__ import division
import sys
from datetime import datetime
import logging
import oai_node
from conf import settings, CustomSettings
import time
from summary import email_exception, PublishSummary
from workspace import Workspace
from datapump.exception import PublishException
import importlib
import os
from optparse import OptionParser
'''
Created on Feb 15, 2013

@author: dfinke
'''

log = logging.getLogger(__name__)

def LogStartStop():
    """ Logging decorator that is not currently being used"""
    start = datetime.utcnow()
    
    def log_start():
        log.info("Started @ {0}".format(start.strftime("%Y-%m-%dT%H:%M:%SZ")))
    
    def log_info(obj_opts):
        config = obj_opts.settings["config"]

        log.info("Harvesting data from: {0}{1} from: {2} until: {3}".format(config["server"], config["path"], config["harvest_from"], config["harvest_until"]))
        log.info("Publishing to: {0}".format(obj_opts.LEARNING_REGISTRY_URL))
    
    def log_error():
        log.exception("An uncaught error occurred")
    
    def log_finish():
        finish = datetime.utcnow()
        dur = finish - start
        dur_secs = (dur.microseconds + (dur.seconds + dur.days * 24 * 3600) * 10**6) / 10**6
        log.info("Finished @ {0}, Duration: {1} seconds".format(finish.strftime("%Y-%m-%dT%H:%M:%SZ"), dur_secs))
    
    
    def decorator(fn):
        def wrapped_fn(self, *args, **kw):
            try:
                log_start()
                log_info(self.opts)
                fn(self, *args, **kw)
            except:
                log_error()
            finally:
                log_finish()
        return wrapped_fn
    return decorator


def publish_collections(collection_set_specs, allow_collection_removal):
    """ Main method that publishes all collections for all
    defined targets """
    try:
        oai_node_obj = oai_node.OAIFetchNode()
        workspace = Workspace(oai_node_obj, allow_collection_removal)
        # sets to publish if nothing is sent in will return a set of collections so that if called
        # every day, by the end of the month no matter what all collections will be ran
        collections = oai_node_obj.get_sets_to_publish(collection_set_specs)
        for targetPath, taragetName in settings.TARGETS:
            try:
                module = importlib.import_module(targetPath)
                target = getattr(module, taragetName)()
            except ImportError as e:
                raise ImportError(
                    "Could not import target '%s' (Is it on sys.path? Is there an import error in the settings file?): %s"
                    % (targetPath, e)
                )

            log.info('Running publish process for target %s' % target)

            #The publish summary is a summary for all collections
            publish_summary = PublishSummary(target.title, target.target_settings['PUBLISH_URL'])
            for collection in collections:
                collection_name = collection[0]
                collection_id = collection[1]
                collection_library_format = collection[2]
                if collection_id:
                    log.info('Starting publishing process for set %s' % collection_name)
                else:
                    log.info('Starting publishing process for all sets.')
                
                # reset couch before we start updating the collection
                workspace.reset_collection()
                workspace.set_collection(target.title, collection_id, collection_name, 
                                         collection_library_format)
               
                try:
                    target.update_collection(workspace)
                except Exception, e:
                    # exceptions should be handled inside the update_collection method, this
                    # really should never occur unless one codes the target wrong
                    publish_exception = PublishException("Un-caught exception during publish.", e)
                    log.error(publish_exception)
                    workspace.collection_summary.add_error(publish_exception)
                finally:
                    # finally email the summary out
                    workspace.collection_summary.email_summary()
                    publish_summary.add_collection_summary(workspace.collection_summary)
                # After the full publish sleep for a bit to let the node indexer catch up
                time.sleep(10)
            
            publish_summary.email_summary()    
            # clean the target if applicaable
            target.clean()
            
    except Exception, e:
        publish_exception = PublishException("Un-caught exception during publish.", e)
        log.error(publish_exception)
        email_exception(publish_exception, "Publishing Failure")
    finally:
        workspace.clean()
        
""" this block is called when the file is ran as a file """
if __name__ == '__main__':
    parser = OptionParser(usage="usage: %prog [options] [setSpec1, setSpec2 etc]",
                          version="%prog 1.0")
    
    parser.add_option("--allow_collection_removal",
                      action="store_true",
                      dest="allow_collection_removal",
                      default=False,
                      help="Allows collections to removed from the LR if their OAI response has 0 records")
     
    parser.add_option("--all",
                      action="store_true",
                      dest="all_collections",
                      default=False,
                      help="Publish all collections found on OAI instead of specifying collections")
    parser.add_option("--settings",
                      action="store",
                      dest="settings",
                      default="local_settings",
                      help="Set the default local settings for the publish. Defaults to local_settings")

    (options, args) = parser.parse_args()
    os.environ[CustomSettings.ENVIRONMENT_VARIABLE] = options.settings
    logging.basicConfig(format="%(asctime)s : %(levelname).8s : %(module)s.%(funcName)s(%(lineno)s) : %(message)s", datefmt='%Y-%m-%dT%H:%M:%S%Z', level=settings.LOG_LEVEL)

    if not args and not options.all_collections:
        log.info("Must either specify at least one setSpec or --all must be set")
    else:
        # If args is None, all collections will be published
        publish_collections(args, options.allow_collection_removal)    