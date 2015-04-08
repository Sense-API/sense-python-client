import urllib
from copy import copy
import requests
from dateutil import parser
import utils
import json

def convert_to_sense_object(k, v):
    """
    Convert json values into a python object. If v is a dict use the "object" key value
    pair to get a hint of which object is relevant (fallback on APIResource).
    The name of the key (k) is used to control how some values are parsed (dates)
    :param k: str
    :param v: object
    :return: object
    """
    dates = ['updatedAt', 'createdAt', 'start', 'end']
    types = {'node': Node, 'feed': Feed, 'user': User,
             'subscription': Subscription, 'list': ListAPIResource}

    if k in dates:
        return parser.parse(v)

    elif isinstance(v, list):
        return [convert_to_sense_object(k, e) for e in v]

    elif isinstance(v, dict):
        klass_name = v.get('object')
        if isinstance(klass_name, basestring):
            klass = types.get(klass_name, APIResource)
        else:
            klass = APIResource
        return klass.construct_from(v)

    else:
        return v

def filter_feeds(feeds):
    for f in feeds:
        if isinstance(f, Feed):
            yield f.uid
        elif isinstance(f, basestring):
            yield f

def prepare_request(params=None):
    """
    This allows each functions using requests to override auth parameters.
    """

    # Find and remove request settings from the parameters
    from . import api_url, api_key, app_secret, user_agent
    if params and 'api_url' in params:
        api_url = params.pop('api_url')
    if params and 'api_key' in params:
        api_key = params.pop('api_key')
    if params and 'app_secret' in params:
        app_secret = params.pop('app_secret')

    # Make a session
    s = requests.Session()
    s.auth = utils.SenseTokenAuth(api_key, app_secret)
    s.headers.update({'User-Agent': user_agent})

    return s, api_url, params


class APIResource(dict):
    def __init__(self, uid=None, **params):
        super(APIResource, self).__init__(**params)

        if uid:
            self['uid'] = uid

    def __str__(self):
        if self.has_key('uid'):
            return self.uid
        else:
            return super(APIResource, self).__str__()


    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError, err:
            raise AttributeError(*err.args)

    @classmethod
    def _class_name(cls):
        if cls == APIResource:
            raise NotImplementedError(
                'APIResource is an abstract class. You should perform '
                'actions on its subclasses (e.g. User, Node)')
        return str(urllib.quote_plus(cls.__name__.lower()))

    @classmethod
    def _class_url(cls):
        return "/%ss/" % (cls._class_name(),)

    def instance_url(self, uid=None):
        if not uid and not self.get('uid'):
            raise ValueError(
                'Could not determine which URL to request: %s instance '
                'has invalid ID: %r' % (type(self).__name__, uid), 'id')

        uid = utils.utf8(self.get('uid', uid))
        extn = urllib.quote_plus(uid)
        return "%s%s/" % (self._class_url(), extn)

    @classmethod
    def construct_from(cls, values):
        instance = cls(values.get('id'))
        instance._refresh_from(values)
        return instance

    @classmethod
    def retrieve(cls, uid, **params):
        instance = cls()
        instance._refresh(uid, params)
        return instance

    def _refresh_from(self, values):
        for k, v in values.iteritems():
            super(APIResource, self).__setitem__(k, convert_to_sense_object(k, v))

    def _refresh(self, uid, params):
        s, api_url, params = prepare_request(params)
        url = api_url + self.instance_url(uid=uid)
        r = s.get(url, params=utils.expand(params))
        r.raise_for_status()
        self._refresh_from(r.json())
        return self


class SingletonAPIResource(APIResource):

    @classmethod
    def retrieve(cls, uid=None, **params):
        return super(SingletonAPIResource, cls).retrieve(None, **params)

    @classmethod
    def _class_url(cls):
        return "/%s/" % (cls._class_name(),)

    def instance_url(self, uid=None):
        return self._class_url()


class ListAPIResource(APIResource):
    """
    The Python client handle pages of results thanks to three methods:

        * `next` and `prev`, returns the adjacent pages of results (or `None` at the beginning and end of the list).
        * `all` returns and iterator on the `objects` attribute of pages that will fetch more pages as a loop iterate over it.

    >>> # page per page navigation
    >>> first_page = sense.Node.list()
    >>> second_page = first_page.next()
    >>> # navigation with an iterator
    >>> for node in sense.Node.all():
    >>>     assert hasattr(node, 'uid')
    """

    @classmethod
    def list(cls, **params):
        s, api_url, params = prepare_request(params)
        url = api_url + cls._class_url()
        r = s.get(url, params=utils.expand(params))
        r.raise_for_status()
        return convert_to_sense_object(None, r.json())

    def next(self):
        if self.get('links') and self.links.get('next'):
            s, _, __ = prepare_request()
            r = s.get(self.links.next)
            r.raise_for_status()
            return self.construct_from(r.json())
        else:
            return

    def prev(self):
        if self.get('links') and self.links.get('prev'):
            s, _, __ = prepare_request()
            r = s.get(self.links.prev)
            r.raise_for_status()
            return self.construct_from(r.json())
        else:
            return

    @classmethod
    def all(cls, **params):
        page = cls.list(**params)
        return page.yield_all()

    def yield_all(self):
        for o in self.objects:
            yield o
        if self.links.next:
            page = self.next()
            for o in page.yield_all():
                yield o


class CreateUpdateAPIResource(APIResource):

    @classmethod
    def create(cls, **params):
        s, api_url, params = prepare_request(params)
        r = s.post(api_url + cls._class_url(), data=params)
        r.raise_for_status()
        return convert_to_sense_object(None, r.json())

    def save(self, **params):
        s, api_url, _ = prepare_request()
        data = self.serialize()
        data.update(params)
        r = s.put(api_url + self.instance_url(), data=data)
        r.raise_for_status()
        if r.status_code == 200:
            return convert_to_sense_object(None, r.json())


class DeleteAPIResource(APIResource):

    def delete(self):
        s, api_url, _ = prepare_request()
        r = s.delete(api_url + self.instance_url())
        r.raise_for_status()
        return None


class User(SingletonAPIResource):
    """
    >>> import sense
    >>> sense.api_key = '{{ api_key }}'
    >>> sense.User.retrieve(expand=['devices'])
    """

    @classmethod
    def api_key(cls, **kwargs):
        """
        >>> import sense
        >>> api_key = sense.User.api_key(username='{{ user.username }}', password='__your_Sen.se_account_password__')
        """
        from . import api_url
        url = api_url + cls._class_url() + 'api_key/'
        r = requests.post(url, data=kwargs)
        r.raise_for_status()
        return r.json().get('token')


class Node(ListAPIResource):

    @property
    def feeds(self):
        return type('Feed', (Feed,), {'node_obj':self})

    @classmethod
    def list(cls, **params):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> sense.Node.list()
        >>> sense.Node.list(resource__type='device', resource__slug='cookie')
        """
        return super(Node, cls).list(**params)

    @classmethod
    def retrieve(cls, uid, **params):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> node = sense.Node.retrieve('{{ node.uid }}')
        """
        return super(Node, cls).retrieve(uid, **params)

    def serialize(self):
        return {
            'label': self.label,
            'subscribes': filter_feeds(self.subscribes),
            'publishes': filter_feeds(self.publishes)
        }


class Feed(ListAPIResource):
    node_obj = None

    def __init__(self, *args, **kwargs):
        super(Feed, self).__init__(*args, **kwargs)
        if self.node_obj:
            self['node_uid'] = self.node_obj['uid']

    @classmethod
    def _class_url(cls):
        if not cls.node_obj:
            return super(Feed, cls)._class_url()
        return ''.join((cls.node_obj.instance_url(), cls._class_name(), 's/'))

    def instance_url(self, uid=None):
        if self.get('node_uid') and (self.get('type') or uid):
            return '{url}{type}/'.format(
                url=self._class_url(), type=self.get('type') or uid)

        elif uid or self.get('uid'):
            f_copy = Feed(uid or self.get('uid'))
            return super(Feed, f_copy).instance_url(uid=uid)

        else:
            raise AttributeError('No uid or node uid + type provided')


    @property
    def events(self):
        """
        This allow all events class to be based on the /events/ endpoint.
         Remove eventual nesting under the /nodes/(uid) endpoint.
        """
        feed = copy(self)
        return type('Event', (Event,), {'feed_obj':feed})()

    @classmethod
    def list(cls, **params):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> node = sense.Node.retrieve('{{ node.uid }}')
        >>> node.feeds.list()
        """
        return super(Feed, cls).list(**params)

    @classmethod
    def retrieve(cls, uid, **params):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> node = sense.Node.retrieve('{{ node.uid }}')
        >>> node.feeds.retrieve('{{ feed.type }}')
        """
        return super(Feed, cls).retrieve(uid, **params)


class Event(APIResource):
    feed_obj = None

    def list(self, **params):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> feed = sense.Feed.retrieve('{{ feed.uid }}')
        >>> feed.events.list(limit=3)
        """
        s, api_url, params = prepare_request(params)
        url = ''.join((api_url, self.feed_obj.instance_url().rstrip('/'), Event._class_url()))
        r = s.get(url, params=params)
        r.raise_for_status()
        return convert_to_sense_object(None, r.json())

    def create(self, **params):
        """
        >>> import sense
        >>> import datetime
        >>> sense.api_key = '{{ api_key }}'
        >>> feed = sense.Feed('{{ feed.uid }}')
        >>> data = {'key': 'value', 'other-key': 'other-value' }
        >>> cur_date = datetime.datetime.utcnow()
        >>> feed.events.create(data=data, dateEvent=cur_date.isoformat())
        """
        s, api_url, params = prepare_request(params)
        url = ''.join((api_url, self.feed_obj.instance_url().rstrip('/'), Event._class_url()))
        r = s.post(url, data=json.dumps(params), headers=dict(s.headers, **{'Content-Type': 'application/json'}))
        r.raise_for_status()


class Subscription(ListAPIResource, CreateUpdateAPIResource, DeleteAPIResource):

    def serialize(self):
        return {
            'label': self.label,
            'gatewayUrl': self.gatewayUrl,
            'subscribes': filter_feeds(self.subscribes)
        }

    @classmethod
    def list(cls, **params):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> sense.Subscription.list()
        """
        return super(Subscription, cls).list(**params)

    @classmethod
    def create(cls, **params):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> sense.Subscription.create(
        >>>     label="my subscription",
        >>>     gatewayUrl="https://example.com/events/",
        >>>     subscribes = ['{{ feed.uid }}']
        >>> )
        """
        return super(Subscription, cls).create(**params)

    def save(self):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> subscription = sense.Subscription.retrieve('{{ subscription.uid }}')
        >>> subscription.gatewayUrl = 'https://example.com/another_endpoint/'
        >>> subscription.save()
        """
        return super(Subscription, self).save()

    def delete(self):
        """
        >>> import sense
        >>> sense.api_key = '{{ api_key }}'
        >>> subscription = sense.Subscription.retrieve('{{ subscription.uid }}')
        >>> subscription.delete()
        """
        return super(Subscription, self).delete()


class Person(ListAPIResource):
    """
    >>> import sense
    >>> sense.api_key = '{{ api_key }}'
    >>> persons = sense.Person.list()
    """
    pass

class Device(ListAPIResource): pass
class Application(ListAPIResource): pass
