import sense

# Authentication
sense.api_key = '__your_api_key__'
# You can get your key using the API.
sense.api_key = sense.User.api_key(username='__your_username__', password='__your_password__')

# Get the first cookie of your account
user = sense.User.retrieve(expand=['devices'])
cookies = [d for d in user.devices if d.resource.slug == 'cookie']
cookie = cookies[0]

# Create a subscription in order to receive new temperature events.
# You will be notified of a new event on a URL of your choice,
sub = sense.Subscription.create(
    label='%s motion feed subscription' % cookie.label,
    gateway_url='https://server2000.eu/events/',
    subscribes= ['/nodes/%s/feeds/temperature/' % cookie.uid]
)
assert sub.uid is not None

# ... edit it,
sub.label = 'new label!'
sub.save()

# ... delete it.
sub.delete()

# Once you know UIDs you can instantiate objects without querying the API.
feed = sense.Node(cookie.uid).feeds(type='motion')

# Get the last 5 events of the motion feed
ev = feed.events.list(limit=5)
assert len(ev.objects) == 5

# Filtering
cookies = sense.Node.list(resource__slug='cookie')
assert cookies.objects[0].resource.slug == 'cookie'

# Collections
nodes = sense.Node.list() # the first page of results
more_nodes = nodes.next() # get the second page of results
# Iterator navigation
for n in sense.Node.all():
    assert hasattr(n, 'uid')