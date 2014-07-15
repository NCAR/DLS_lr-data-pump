import argparse, base64, uuid, json, urllib2
from LRSignature.sign.Sign import Sign_0_21
from datapump.targets.lr import settings as lr_settings
from LRSignature.verify import Verify
headers = {
    "content-type": "application/json; charset=utf-8"
}

server = "http://sandbox.learningregistry.org"

def create_verifytool():
        """ Create a verify tool, that uses the LRSignature Module """
             
        gpg = {}
        if lr_settings.GRG_BIN:
            gpg["gpgbin"] = lr_settings.GRG_BIN
        if lr_settings.GNUPG_HOME:
            gpg["gnupgHome"] = lr_settings.GNUPG_HOME
        return Verify.Verify_0_21(**gpg)

        
if "__main__" == __name__:
    document = {"doc_ID": "02a6e9432c09481cb6c342ef3c7e7280", "resource_data_description": {"doc_type": "resource_data", "resource_locator": "http://www.teachersdomain.org/resource/psu08-liq.sci.wastewater/", "digital_signature": {"key_location": ["https://keyserver2.pgp.com/vkd/DownloadKey.event?keyid=0x0C9700F7B292EAAA"], "key_owner": "Dave Finke (Second pgp key) <dfinke@ucar.edu>", "signing_method": "LR-PGP.1.0", "signature": "-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA1\n\n12a74f9fb236445c7a27b1b68699ba50ad0b28057e62849ad6497f9260f8f902\n-----BEGIN PGP SIGNATURE-----\nVersion: GnuPG v1.4.13 (Cygwin)\n\niQEcBAEBAgAGBQJRknFiAAoJEAyXAPeykuqqDlYH/0CinFgCv/GfmIlI+b4e/tcO\nMv0yc1vZ/25UC4KY9G3k2AxIx19USWvfSFyuQ+KS5jWfmEq7g/jnZ8N4F5I7E06N\ne67qlgktqmTiNSdXuX283bX8Ss7DdJICeI0UR0LAcCltJyixWmJU0a38w6jLyo3k\n9olYZkUJS3brBoVaG3VrpyFl6TJioEQK9LH07VFjDcTBx9Sp1/buZkUG2ljXm0h+\nswAnV88lpVKvzgo8g5bI0tEWlUqDZkABsMFgV1acHk7oBDAbn/b0jb0tKC/d76Ju\nsgY19OVLyFl8puKtMIBq4h8gADhYu5FOaXCTrYGKyn69yC7ROtHNmnyPe7mZ2PM=\n=04Rt\n-----END PGP SIGNATURE-----\n"}, "resource_data": {"items": [{"id": "oai:nsdl.org:2200/20120828120523541T", "activity": {"content": "Paradata for Liquid Assets: Wastewater", "verb": {"action": "commented", "date": "2008-11-20T00:00:00/2012-08-01T15:41:05.677196", "measure": {"measureType": "count", "value": "1.0"}}, "actor": {"objectType": "Educator"}, "object": "http://www.teachersdomain.org/resource/psu08-liq.sci.wastewater/"}}, {"id": "oai:nsdl.org:2200/20120828120523541T", "activity": {"content": "Paradata for Liquid Assets: Wastewater", "verb": {"action": "rating", "date": "2008-11-20T00:00:00/2012-08-01T15:41:05.677196", "measure": {"scaleMin": 1, "measureType": "star average", "scaleMax": 5, "sampleSize": 1, "value": "5.0"}}, "actor": {"objectType": "Educator"}, "object": "http://www.teachersdomain.org/resource/psu08-liq.sci.wastewater/"}}]}, "keys": ["paradata", "NSDL_COLLECTION_ncs-NSDL-COLLECTION-000-003-112-089", "oai:nsdl.org:2200/20120828120523541T"], "TOS": {"submission_TOS": "http://www.learningregistry.org/information-assurances/open-information-assurances-1-0"}, "_rev": "1-88c455a4b5f6aedc99e166c9459e7a71", "resource_data_type": "metadata", "payload_placement": "inline", "payload_schema": ["LR Paradata 1.0", "application/microdata+json"], "node_timestamp": "2013-04-08T11:50:51.234547Z", "doc_version": "0.49.0", "create_timestamp": "2013-04-08T11:50:51.234547Z", "update_timestamp": "2013-04-08T11:50:51.234547Z", "active": True, "publishing_node": "bababe6a3288497fb7a46d454154f5db", "_id": "02a6e9432c09481cb6c342ef3c7e7280", "doc_ID": "02a6e9432c09481cb6c342ef3c7e7280", "identity": {"signer": "NSDL", "submitter": "NSDL", "submitter_type": "agent", "curator": "NSDL"}}}
    is_valid_signature = create_verifytool().verify(document['resource_data_description'])
    print is_valid_signature





