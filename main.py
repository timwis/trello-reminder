import os
from os.path import join, dirname
import json
from urllib import urlencode
import urllib2
from datetime import datetime
import dateutil.parser

from dotenv import load_dotenv
import pytz
import mandrill
from jinja2 import Environment, PackageLoader

# Load environment variables
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

env = {}
for name in [
    'MIN_DAYS',
    'TRELLO_KEY',
    'TRELLO_TOKEN',
    'TRELLO_BOARD',
    'MANDRILL_KEY',
    'MSG_FROM_EMAIL',
    'MSG_FROM_NAME',
    'MSG_SUBJECT',
    'MEMBER_EMAILS',
  ]:
  env[name] = os.environ.get(name)

mandrill_client = mandrill.Mandrill(env['MANDRILL_KEY'])

# Prepare template
template_env = Environment(loader=PackageLoader(__name__, 'templates'))
template = template_env.get_template('reminder_email.html')

# Split member emails into a dict
member_emails = {}
member_email_lines = env['MEMBER_EMAILS'].split(',')
for member_email_line in member_email_lines:
  member_email_line_parts = member_email_line.split(':')
  member_emails[member_email_line_parts[0].strip()] = member_email_line_parts[1].strip()

# Querystring parameters
params = {
  'key': env['TRELLO_KEY'],
  'token': env['TRELLO_TOKEN'],
  'fields': 'name,url,dateLastActivity',
  'members': 'true'
}

# Construct trello URL and fetch
url = 'https://api.trello.com/1/boards/' + env['TRELLO_BOARD'] + '/cards?' + urlencode(params)
cards = json.load(urllib2.urlopen(url))

today = datetime.now(pytz.utc)
members = {}

# For each card that's older than a week
for card in cards:
  dateLastActivity = dateutil.parser.parse(card[u'dateLastActivity'])
  if abs(today - dateLastActivity).days > int(env['MIN_DAYS']):
    # Add card to each member's list
    for member in card[u'members']:
      username = str(member[u'username'])
      if username not in members:
        members[username] = []
      members[username].append(card)

# For each member
for username, cards in members.iteritems():
  if username not in member_emails:
    continue

  # Build message data
  message = {
    'subject': env['MSG_SUBJECT'],
    'from_email': env['MSG_FROM_EMAIL'],
    'from_name': env['MSG_FROM_NAME'] or env['MSG_FROM_EMAIL'],
    'to': [{
      'email': member_emails[username],
      'name': username,
      'type': 'to'
    }],
    # Construct HTML from template
    'html': template.render(num_days=env['MIN_DAYS'], cards=cards)
  }

  # Send email
  try:
    result = mandrill_client.messages.send(message=message)
    print(result)
  except mandrill.Error as e:
    print('A mandrill error occurred: %s - %s' % (e.__class__, e))
    raise