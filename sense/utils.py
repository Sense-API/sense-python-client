import sys
from requests.auth import AuthBase

def utf8(value):
    if isinstance(value, unicode) and sys.version_info < (3, 0):
        return value.encode('utf-8')
    else:
        return value

def process_params(d):
    r = {}
    for k, v in d.items():
        if k == 'expand':
            r['expand[]'] = v
        else:
            r[k] = v
    return r


class DRFTokenAuth(AuthBase):
    """
    Attaches Django Rest Framework token auth header to the given Request object.
    http://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication
    http://docs.python-requests.org/en/latest/user/authentication/#new-forms-of-authentication
    """
    def __init__(self, api_key):
        self.api_key = api_key

    def __call__(self, r):
        r.headers['Authorization'] = " Token %s" % self.api_key
        return r