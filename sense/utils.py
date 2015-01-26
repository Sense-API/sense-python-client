import sys
from requests.auth import AuthBase
import hmac, hashlib

def utf8(value):
    if isinstance(value, unicode) and sys.version_info < (3, 0):
        return value.encode('utf-8')
    else:
        return value

def expand(d):
    r = {}
    for k, v in d.items():
        if k == 'expand':
            r['expand[]'] = v
        else:
            r[k] = v
    return r


class SenseTokenAuth(AuthBase):
    """
    Attaches Sen.se token auth header to the given Request object.
    http://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication
    http://docs.python-requests.org/en/latest/user/authentication/#new-forms-of-authentication
    """
    def __init__(self, api_key, app_secret=None):
        self.api_key = api_key
        self.app_secret = app_secret

    def __call__(self, r):
        if self.app_secret:
            token = hmac.new(self.app_secret, msg=self.api_key, digestmod=hashlib.sha512).hexdigest()
        else:
            token = self.api_key

        r.headers['Authorization'] = " Token %s" % token
        return r