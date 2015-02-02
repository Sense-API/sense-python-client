__author__ = 'pierre'

import unittest
from copy import deepcopy
import datetime
import json
from getpass import getpass
import requests
import httpretty
import sense
from sense.resources import APIResource, ListAPIResource

DEFAULT_USER = 'demoone' 
API_URL = 'https://sen.se/api/v2'

DUMMY_NODE = {
    "object": "node",
    "url": "http://127.0.0.1:8200/api/v2/nodes/testuid/",
    "uid": "testuid",
    "createdAt": "2014-04-01T15:56:12",
    "updatedAt": "2014-07-12T12:16:12",
    "label": "node__dummy",
    "paused": False,
    "subscribes": [
         {
             "object": "feed",
             "url": "http://127.0.0.1:8200/api/v2/feeds/OlkQpUi5x4rS8RyxNOpKYR9CrPrGuhWg/",
             "uid": "OlkQpUi5x4rS8RyxNOpKYR9CrPrGuhWg",
             "label": "Profile",
             "type": "profile"
         }
    ],
    "publishes": [
         {
             "object": "feed",
             "url": "http://127.0.0.1:8200/api/v2/feeds/AiX2oDNRjswKT9yxMAXNAgxcGBqeHX7P/",
             "uid": "AiX2oDNRjswKT9yxMAXNAgxcGBqeHX7P",
             "label": "Motion",
             "type": "motion"
         },
    ]
}

PAGE = {
    'object': 'list',
    'links': {
        'next': sense.api_url + '/nodes/?page=2',
        'prev': None
    },
    'totalObjects': 9,
    'objects': []
}

DUMMY_EVENT = {
    "profile": None,
    "dateServer": None,
    "signal": None,
    "dateEvent": "2014-04-16T12:39:11.542637",
    "version": None,
    "data": {
        "message": "Mother was connected during 0:04:02.032074"
    },
    "payload": "Mother was connected during 0:04:02.032074",
    "nodeUid": "6gqyjjGi0WMYa12pzT7cPgQ3H6M9gKYr"
}

DUMMY_NODES_PAGE = deepcopy(PAGE)
DUMMY_NODES_PAGE['objects'] = [DUMMY_NODE for _ in range(0,5)]

DUMMY_EVENTS_PAGE = deepcopy(PAGE)
DUMMY_EVENTS_PAGE['links']['next'] = None
DUMMY_EVENTS_PAGE['objects'] = [DUMMY_EVENT for __ in range(0,5)]

DUMMY_USER = {
    'object': 'user',
    'username': 'user__dummy',
    'country': 'FR',
    'createdAt': '2014-04-01T09:29:58',
    'updatedAt': '2014-04-01T09:29:58',
    'devices': [DUMMY_NODE]
}

DUMMY_SUBSCRIPTION = {
    "object": "subscription",
    "url": "http://127.0.0.1:8200/api/v2/nodes/test_uid/",
    "uid": "testuid",
    "createdAt": "2014-12-04T16:28:09",
    "updatedAt": "2014-12-04T16:28:09",
    "label": "subscription__dummy",
    "paused": False,
    "subscribes": [
        {
            "object": "feed",
            "url": "http://127.0.0.1:8200/api/v2/feeds/eJXayFlDihokjC00D8NFXXeIQnjF4R5x/",
            "uid": "eJXayFlDihokjC00D8NFXXeIQnjF4R5x",
            "label": "Presence",
            "type": "presence"
        }
    ],
    "publishes": [],
    "resource": {
        "object": "resource",
        "url": "http://127.0.0.1:8200/api/v2/resources/subscription/",
        "type": "subscription",
        "slug": "subscription"
    },
    "gatewayUrl": "https://yodel.eu",
}

DUMMY_FEED = {
    "object": "feed",
    "url": "http://127.0.0.1:8200/api/v2/feeds/testuid/",
    "uid": "testuid",
    "label": "Presence",
    "type": "presence"
}


class TestUtils(unittest.TestCase):

    def test_process_params(self):
        from sense.utils import expand
        d = expand({
            'expand': ['devices','applications'],
            'limit': 12
        })
        self.assertTrue(d.has_key('expand[]'))
        self.assertEqual(d['limit'], 12)


class TestAPIResource(unittest.TestCase):

    def test_init(self):
        u = APIResource('myuid', username='pierre')

        self.assertIsNotNone(u.uid)
        self.assertEqual(u.username, 'pierre')

    def test_refresh_from(self):
        u = APIResource()
        u._refresh_from({
            'username': 'pierre',
            'createdAt': '2014-04-01T09:29:58'
        })

        self.assertEqual(u.username, 'pierre')
        self.assertEqual(u.get('username'), 'pierre')
        self.assertIsInstance(u.createdAt, datetime.datetime)
        self.assertRaises(AttributeError, lambda: u.blah)
        self.assertRaises(NotImplementedError, lambda: APIResource._class_name())
        self.assertRaises(ValueError, lambda: u.instance_url())

    def test_repr(self):
        u = APIResource()
        d = {
            'username': 'pierre',
            'createdAt': '2014-04-01T09:29:58',
            'uid': 'blahblablablalblablu'
        }
        u._refresh_from(d)

        self.assertEqual("%s" % u, d.get('uid'))


class TestFeed(unittest.TestCase):
    def test_instance_url(self):
        feed = sense.Node('node-uid').feeds('feed-uid')
        self.assertEqual(feed.instance_url(), '/feeds/feed-uid/')

        feed = sense.Node('node-uid').feeds(type='alert')
        self.assertEqual(feed.instance_url(), '/nodes/node-uid/feeds/alert/')

        feed = sense.Feed('feed-uid')
        self.assertEqual(feed.instance_url(), '/feeds/feed-uid/')

        feed = sense.Node('node-uid').feeds()
        self.assertRaises(AttributeError, feed.instance_url)

        self.assertEqual(sense.Node('node-uid').feeds._class_url(), '/nodes/node-uid/feeds/')


class TestSubscription(unittest.TestCase):

    def test_serialize(self):

        s = sense.Subscription.construct_from(DUMMY_SUBSCRIPTION)
        s.subscribes.append('another_feed_uid_or_url')

        d = s.serialize()
        for e in d.get('subscribes'):
            self.assertIsInstance(e, basestring)


class TestIntegration(unittest.TestCase):

    def setUp(self):
        httpretty.enable()

        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/nodes/testuid/',
            body=json.dumps(DUMMY_NODE),
            content_type='application/json')

        page2 = deepcopy(DUMMY_NODES_PAGE)
        page2['links']['prev'] = sense.api_url + '/nodes/?page=1'
        page2['links']['next'] = None
        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/nodes/',
            responses=[
                httpretty.Response(body=json.dumps(DUMMY_NODES_PAGE)),
                httpretty.Response(body=json.dumps(page2))
            ]
        )


    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

    def test_User(self):
        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/user/',
            body=json.dumps(DUMMY_USER),
            content_type='application/json')

        u = sense.User.retrieve()

        self.assertEqual(u.username, 'user__dummy')
        self.assertEqual(u.country, 'FR')
        self.assertIsInstance(u.updatedAt, datetime.datetime)
        self.assertIsInstance(u.devices[0], sense.Node)

    def test_Node_retrieve(self):
        node = sense.Node.retrieve('testuid')

        self.assertEqual(node.label, 'node__dummy')
        self.assertIsInstance(node.subscribes[0], sense.Feed)

    def test_Node_list(self):
        nodes = sense.Node.list()

        self.assertEqual(nodes.totalObjects, 9)
        self.assertEqual(len(nodes.objects), 5)
        self.assertIsInstance(nodes.objects[0], sense.Node)
        self.assertIsNone(nodes.prev())

        nodes2 = nodes.next()

        self.assertIsNotNone(nodes2)
        self.assertIsNotNone(nodes2.prev())
        self.assertIsNone(nodes2.next())
        self.assertIsInstance('%s' % nodes, str)

    def test_Node_all(self):
        i = 0
        for i, node in enumerate(sense.Node.all()):
            self.assertTrue(hasattr(node, 'uid'))
        self.assertEqual(i,9)

    """
    def test_Node_create(self):
        httpretty.register_uri(
            httpretty.POST, sense.api_url + '/nodes/',
            body=json.dumps(DUMMY_NODE),
            content_type='application/json')

        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/nodes/',
            body=json.dumps({'objects': [DUMMY_NODE]}),
            content_type='application/json')

        s = sense.Node.create(
            label= 'my new node',
            subscribes= ['eJXayFlDihokjC00D8NFXXeIQnjF4R5x'],
            publishes= ['AiX2oDNRjswKT9yxMAXNAgxcGBqeHX7P']
        )

        self.assertEqual(s.uid, 'testuid')
        self.assertIsInstance(s, sense.Node)

        sl = sense.Node.list()

        self.assertIsInstance(sl.objects[0], sense.Node)

    def test_Node_save(self):
        node_uid = 'testuid'
        new_label = 'new label'
        dummy_node = deepcopy(DUMMY_NODE)
        dummy_node.update({'uid': node_uid})

        updated_node = deepcopy(dummy_node)
        updated_node.update({'label': new_label})

        httpretty.register_uri(
            httpretty.PUT, sense.api_url + '/nodes/' + node_uid + '/',
            body=json.dumps(updated_node),
            content_type='application/json'
        )

        node = sense.Node(node_uid)
        node.update({'label': new_label,
                     'subscribes': dummy_node['subscribes'],
                     'publishes': dummy_node['publishes']})
        result = node.save()
        self.assertEqual(result.uid, node.uid)
    """

    def test_Node_serialize(self):
        node = sense.Node.retrieve('testuid')

        serialized = node.serialize()
        self.assertItemsEqual(serialized.keys(), ['label', 'subscribes', 'publishes'])
        self.assertEqual(serialized['label'], 'node__dummy')

        # Check that publishes and subscribes contain only the specified feed uid
        self.assertEqual(list(serialized['subscribes']), ['OlkQpUi5x4rS8RyxNOpKYR9CrPrGuhWg'])
        self.assertEqual(tuple(serialized['publishes']), ('AiX2oDNRjswKT9yxMAXNAgxcGBqeHX7P',))

    def test_Subscription_create(self):
        httpretty.register_uri(
            httpretty.POST, sense.api_url + '/subscriptions/',
            body=json.dumps(DUMMY_SUBSCRIPTION),
            content_type='application/json')

        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/subscriptions/',
            body=json.dumps({'objects': [DUMMY_SUBSCRIPTION]}),
            content_type='application/json')

        s = sense.Subscription.create(
            label= 'my new sub',
            gatewayUrl= 'https://yodel.eu',
            subscribes= ['eJXayFlDihokjC00D8NFXXeIQnjF4R5x']
        )

        self.assertEqual(s.uid, 'testuid')
        self.assertIsInstance(s, sense.Subscription)

        sl = sense.Subscription.list()

        self.assertIsInstance(sl.objects[0], sense.Subscription)

    def test_Subscription_save_delete(self):
        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/subscriptions/testuid/',
            body=json.dumps(DUMMY_SUBSCRIPTION),
            content_type='application/json')
        httpretty.register_uri(
            httpretty.PUT, sense.api_url + '/subscriptions/testuid/',
            body=json.dumps(DUMMY_SUBSCRIPTION),
            content_type='application/json')
        httpretty.register_uri(
            httpretty.DELETE, sense.api_url + '/subscriptions/testuid/',
            body=None,
            content_type='application/json')

        s = sense.Subscription.retrieve('testuid')
        s = s.save()
        self.assertEqual(s.uid, 'testuid')
        self.assertIsInstance(s, sense.Subscription)
        self.assertIsNone(s.delete())

    def test_Event_list(self):
        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/feeds/testuid/',
            body=json.dumps(DUMMY_FEED),
            content_type='application/json')
        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/feeds/testuid/events/',
            body=json.dumps(DUMMY_EVENTS_PAGE),
            content_type='application/json')

        feed = sense.Feed.retrieve('testuid')
        events = feed.events.list()
        self.assertIsInstance(events, ListAPIResource)

    def test_Event_create(self):
        httpretty.register_uri(
            httpretty.POST, sense.api_url + '/feeds/testuid/events/',
            body=json.dumps(DUMMY_EVENT),
            content_type='application/json')

        sense.Feed('testuid').events.create(**DUMMY_EVENT)
        self.assertEqual(json.loads(httpretty.last_request().body), DUMMY_EVENT)

        httpretty.register_uri(
            httpretty.POST, 'http://custom_url.com' + '/feeds/testuid/events/',
            body=json.dumps(DUMMY_EVENT),
            content_type='application/json')

        params = {'api_url': 'http://custom_url.com'}
        params.update(DUMMY_EVENT)
        sense.Feed('testuid').events.create(**params)

        params['api_key'] = 'apikey'
        sense.Feed('testuid').events.create(**params)
        last_request = httpretty.last_request()
        self.assertEqual(last_request.headers.get('Authorization'), 'Token apikey')
        self.assertEqual(last_request.headers.get('User-Agent'), sense.user_agent)

    def test_nested_Feeds(self):

        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/nodes/testuid/feeds/',
            body=json.dumps({'objects': [{'object': 'feed'}]})
        )

        httpretty.register_uri(
            httpretty.GET, sense.api_url + '/nodes/testuid/feeds/testtype/',
            body=json.dumps({'object': 'feed'})
        )

        node = sense.Node.retrieve('testuid')
        self.assertIsInstance(node, sense.Node)

        feeds = node.feeds.list()
        self.assertIsInstance(feeds.objects[0], sense.Feed)

        feed = node.feeds.retrieve('testtype')
        self.assertIsInstance(feed, sense.Feed)

    def test_nested_token(self):
        dummy_token = 'blah'
        httpretty.register_uri(
            httpretty.POST, sense.api_url + '/user/api_key/',
            body=json.dumps({'token': dummy_token})
        )

        t = sense.User.api_key(username='pierre', password='********')
        self.assertEqual(t, dummy_token)

# @unittest.skip("Skipping test hitting a live server")
class TestsIntegrationLiveServer(unittest.TestCase):
    fixtures = None

    @classmethod
    def setUpClass(cls):
        u = DEFAULT_USER # the name of a sen.se user with a node and a subscription
        p = getpass() # ... its password
        sense.api_url = API_URL
        sense.api_key = sense.User.api_key(username=u, password=p)
        r = requests.get(sense.api_url +  '/docinfo/', auth=(u, p))
        cls.fixtures = r.json()

    def test_User(self):

        u = sense.User.retrieve()

        self.assertIsInstance(u.username, unicode)
        self.assertIsInstance(u.updatedAt, datetime.datetime)
        self.assertIsInstance(u.applications, list)

        u = sense.User.retrieve(expand=['devices'])

        self.assertTrue(hasattr(u.devices[0],'resource'))

    def test_Node_list(self):

        nodes = sense.Node.list()

        self.assertTrue(nodes.has_key('objects'))
        self.assertIsInstance(nodes.totalObjects, int)
        self.assertIsNone(nodes.prev())

        page_2 = nodes.next()

        try:
            self.assertTrue(page_2.has_key('objects'))
            self.assertTrue(page_2.prev().has_key('objects'))
        except AttributeError:
            self.assertIsNone(page_2)
            self.assertIsNone(nodes.prev())


    def test_Node_all(self):

        i = 0
        for node in sense.Node.all():
            self.assertTrue(hasattr(node, 'uid'))
            i += 1
        nodes = sense.Node.list()
        self.assertEqual(i, nodes.totalObjects)

    def test_Node_list_params(self):

        devices = sense.Node.list(resource__type='device')
        cookies = sense.Node.list(resource__slug='cookie')

        p = len(cookies.objects) <= len(devices.objects)
        self.assertTrue(p)

    def test_Node_retrieve(self):
        uid = self.fixtures.get('node_uid')

        node = sense.Node.retrieve(uid)

        self.assertEqual(node.uid, uid)
        self.assertIsInstance(node, sense.Node)
        self.assertTrue(hasattr(node.feeds,'list'))

        feeds = node.feeds.list()

        self.assertIsInstance(feeds, ListAPIResource)

        motion = node.feeds.retrieve('motion')

        self.assertIsInstance(motion, sense.Feed)

    def test_Subscription_list(self):

        s = sense.Subscription.list()

        self.assertIsInstance(s.objects[0], sense.Subscription)

        my_s = s.objects[0]

        self.assertIsInstance(my_s.subscribes[0], sense.Feed)

    def test_Subscription_create_update_delete(self):

        s = sense.Subscription.create(
                label='my new sub',
                gatewayUrl='https://yodel.eu',
                subscribes=[self.fixtures.get('feed_uid')]
        )

        self.assertIsNotNone(s.uid)
        self.assertIsInstance(s, sense.Subscription)

        s.label = new_label = 'my new label'
        updated_s = s.save()

        self.assertEqual(updated_s.label, new_label)

        self.assertIsNone(s.delete())

    def test_Feed_list(self):
        feed = sense.Feed.list()
        self.assertIsNotNone(feed)

    def test_Feed_retrieve(self):
        uid = self.fixtures['feed_uid']
        feed = sense.Feed.retrieve(uid, expand=['node'])

        self.assertIsInstance(feed.node, sense.Node)

        feed = sense.Feed.retrieve(uid)

        self.assertIsInstance(feed.node, basestring)

    def test_Events_list(self):
        uid = self.fixtures['feed_uid']
        feed = sense.Feed.retrieve(uid)

        self.assertIsInstance(feed, sense.Feed)

        events = feed.events.list(limit=3)

        self.assertEqual(events.totalObjects, 3)

    def test_Events_nested_list(self):
        uid = self.fixtures['node_uid']
        node = sense.Node.retrieve(uid)
        motion = node.feeds.retrieve('motion')
        events = motion.events.list(limit=4)

        self.assertEqual(events.totalObjects, 4)


if __name__ == '__main__':
    unittest.main()
