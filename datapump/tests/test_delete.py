import argparse, base64, uuid, json, urllib2
from LRSignature.sign.Sign import Sign_0_21
import time
headers = {
    "content-type": "application/json; charset=utf-8"
}

server = "http://sandbox.learningregistry.org"


def make_id():
    uid =  "urn:www.example.com:uuid1:%s" % uuid.uuid1()
    version = 0
    while True:
        yield "{uid}-{version}".format(uid=uid, version=version)
        version += 1



def sign_and_publish(doc, key, passphrase):
    signer = Sign_0_21(key, passphrase, gpgbin="gpg", publicKeyLocations=["http://pool.sks-keyservers.net:11371/pks/lookup?op=get&search=0x875464AF5BD2A7A7"])

    signed = signer.sign(doc)

    return signed

   

if "__main__" == __name__:

    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help="publish user", required=True)
    parser.add_argument('-pw', '--passwd', help="publis passwd", required=True)
    parser.add_argument('-s', '--submitter', help="submitter", default="dfinke@ucar.edu")
    parser.add_argument('-p', '--passphrase', help="GPG Passphrase", default=None)
    parser.add_argument('-k', '--key', help="GPG Key ID", default="A8A790EA220403B7")
    args = parser.parse_args()

    published_ids = []

    with open("./replacment-data.json") as f:
        pwd_str = "%s:%s" % (args.user, args.passwd )
        auth_header = {
            "Authorization": "Basic {0}".format(base64.b64encode(pwd_str))
        }

        auth_header.update(headers)

        docs = json.load(f)

        
        id_gen = make_id()
        for idx, doc in enumerate(docs["documents"]):

            published_ids.append(id_gen.next())

            doc["doc_ID"] = published_ids[-1]
            doc["identity"]["submitter"] = args.submitter

            if len(published_ids) > 1:
                doc["replaces"] = published_ids[-2:-1]

            signed = sign_and_publish(doc, args.key, args.passphrase)

            print signed, "\n"

            request = urllib2.Request("%s/publish" % server, headers=auth_header)
            resp = urllib2.urlopen(request, data=json.dumps({ "documents":[signed] }))

            print resp.read(), "\n\n"
            time.sleep(60)