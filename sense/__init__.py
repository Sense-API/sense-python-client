# Sen.se API client
# API docs at https://sen.se/api/v2/docs/

# Configuration
api_url = 'https://sen.se/api/v2'

# Auth
api_key = None
app_secret = None

user_agent = 'Sen.se python client'

from resources import User, Node, Feed, Subscription, Event, Device, Application
from version import VERSION
