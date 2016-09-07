import ucwa.actions as actions
from ucwa.config import load_config
import ucwa.events
from ucwa.events import process_events

from contextlib import closing
import requests.exceptions

import yaml
import argparse
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

args = argparse.ArgumentParser()
args.add_argument('-r', '--register', action="store_true", help="register application")

instance_args = args.parse_args()

if instance_args.register:
    from ucwa.auth import get_signin_url
    import webbrowser

    print('make sure you run `python -m ucwa.http` simultaneously.')

    config = load_config()

    url = get_signin_url(config['redirect_uri'] + '/token', config['client_id'],
                         config['domain'], config['app_id'])

    # Open URL in a new tab, if a browser window is already open.Which it probably is in 2016
    webbrowser.open_new_tab(url)
    exit()

with open('instance.yml', 'r') as instance_f:
    instance_config = yaml.load(instance_f)

config = load_config()

resource = instance_config['resource']
token = instance_config['token']

logging.info('registering application against UCWA api')
try:
    app = actions.register_application(resource, token, config)
except requests.exceptions.HTTPError as he:
    logging.error("Error registering the application, your token might be out of date, run `python authhelper.py` again. - %s " % he.message)
    exit(-1)

logging.info('Registered app %s' % app['id'])
logging.info('listening for events')

event_url = resource + app['_links']['events']['href']
logging.info('setting status to available')

available = actions.set_available(resource, app['id'], token, config)

events_stream = actions.oauth_stream_request(event_url, token, config['redirect_uri'])

event_list = {}


def handle_message(inbound_message, thread_uri, resource):
    # I have a string (message) and some context (dict(uri:thread_uri, resource:resource))
    # how do I get that into stackstorm to execute the alias.
    pass

ucwa.events.MESSAGE_CALLBACK = handle_message

while True:
    with closing(events_stream) as r:
        # Do things with the response here.
        event_response = events_stream.json()

    # get communication events
    comm_evt = [e for e in event_response['sender']]

    if len(comm_evt) > 0:
        event_list = comm_evt[0]['events']
        process_events(event_list, resource, token, config)

    events_stream = actions.oauth_stream_request(
        resource + event_response['_links']['next']['href'],
        token,
        config['redirect_uri'])

