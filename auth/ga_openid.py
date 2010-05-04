from __future__ import with_statement
import array
import base64
import os
import re
import sys
import urllib
from xml.dom.minidom import parseString
from google.appengine.api import memcache, urlfetch
from openid.consumer.discover import OpenIDServiceEndpoint


HOST_META_URL = 'https://www.google.com/accounts/o8/.well-known/host-meta?%s'
RE_LINK = re.compile(r'Link: <(.*)>')


DS_NS = 'http://www.w3.org/2000/09/xmldsig#'
# Got from: http://www.gstatic.com/GoogleInternetAuthority/GoogleInternetAuthority.crt
GOOGLE_CA_FILE = 'auth/GoogleInternetAuthority.crt'
CERT_START = '-----BEGIN CERTIFICATE-----'
CERT_END = '-----END CERTIFICATE-----'


def _fetch_host_meta(domain):
    """Get the URL for XRDS file."""
    key = 'HOST_META:%s' % domain
    cached_value = memcache.get(key)
    if cached_value is not None:
        return cached_value

    host_meta_url = HOST_META_URL % urllib.urlencode({'hd': domain})
    result = urlfetch.fetch(host_meta_url)
    if result.status_code not in (200, 206):
        return None
    match = RE_LINK.match(result.content)
    if match is None:
        return None

    memcache.set(key, match.group(1))
    return match.group(1)


def _get_asn1_length(p):
    first_length = p.get(1)
    if first_length > 127:
        length_length = first_length & 0x7f
        return p.get(length_length)
    else:
        return first_length


def _get_bytes_to_sign(bytes):
    """ASN1Parser's getChild(n) returns new ASN1Parser, but this new instances
    doesn't expose all the bytes of the record. It skips 1 byte for the record
    type and then a number of bytes for the record length. We have to add these
    bytes back in order to check the signature.

    """
    from gdata.tlslite.utils.codec import Parser
    to_sign = array.array('B')
    p = Parser(bytes)
    p.get(1)
    _get_asn1_length(p)
    to_sign.append(p.get(1))
    index_start = p.index
    length = _get_asn1_length(p)
    index_end = p.index
    to_sign.extend(bytes[index_start:index_end])
    to_sign.extend(bytes[index_end:index_end+length])
    return to_sign


def _cert_pub_key(cert):
    """The x.509 certificate is a ASN1-DER-encoded structure consisting of 3
    subrecords:
        - tbsCertificate,
        - signatureAlgorithm,
        - signature.
    These subrecords are accessed with ASN1Parser's getChild(n) method.

    We have to extract certificate's public key, which is embedded in the
    tbsCertificate structure, but first we need to check if this certificate
    comes from Google, and so we check if it's signed with
    GoogleInternetAuthority.crt.

    Signature verification works as follows:
    - we get the tbsCertificate structure bytes - unfortunately p.getChild(0)
      doesn't get all the bytes needed (first four bytes are skipped, and so we
      have to add them in _get_bytes_to_sign);
    - we get the signature from the certificate - p.getChild(2);
    - we extract the public key from GoogleInternetAuthority.crt;
    - we verify that tbsCertificate was signed by Google with hashAndVerify
      method.

    """
    from gdata.tlslite.X509 import X509
    from gdata.tlslite.utils.ASN1Parser import ASN1Parser
    if not cert.startswith(CERT_START):
        cert = '\n'.join((CERT_START, cert, CERT_END))
    cert = X509().parse(cert)
    ca_file = os.path.join(sys.path[0], GOOGLE_CA_FILE)
    with open(ca_file) as f:
        ca_cert = X509().parse(f.read())
    p = ASN1Parser(cert.bytes)
    signature = p.getChild(2).value
    to_sign = _get_bytes_to_sign(cert.bytes)
    if ca_cert.publicKey.hashAndVerify(signature, to_sign):
        return cert.publicKey
    else:
        return None


def _fetch_xrds(domain, url):
    """Fetch the XRDS file and verify embedded certificate is signed by Google
    and XRDS document is properly signed as well.

    """
    key = 'XRDS:%s' % url
    cached_xrds = memcache.get(key)
    if cached_xrds is not None:
        return cached_xrds

    result = urlfetch.fetch(url)
    if result.status_code not in (200, 206):
        return None

    try:
        cert = parseString(result.content).getElementsByTagNameNS(
            DS_NS, 'X509Certificate')[0].childNodes[0].data.strip()
    except Exception:
        return None

    pub_key = _cert_pub_key(cert)
    if pub_key is None:
        return None

    signature = base64.b64decode(result.headers.get('signature', ''))
    sig_bytes = array.array('B', signature)
    if not pub_key.hashAndVerify(sig_bytes, result.content):
        return None

    memcache.set(key, result.content)
    return result.content


def discover_google_apps(domain):
    """Performs Google Apps-specific OpenID discovery.

    Details are here:
    http://tinyurl.com/google-federated-login

    Ruby library used as a base for the below implementation:
    http://tinyurl.com/gapps-openid-ruby

    """
    url = _fetch_host_meta(domain)
    if url is None:
        raise Http404

    xrds = _fetch_xrds(domain, url)
    if xrds is None:
        raise Http404

    return OpenIDServiceEndpoint.fromXRDS(domain, xrds)[0]

