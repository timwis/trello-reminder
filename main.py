import os
import urlparse

from dotenv import load_dotenv
from jinja2 import Environment, PackageLoader
import requests
import mandrill
import arrow

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
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
print(env)
mandrill_client = mandrill.Mandrill(env['MANDRILL_KEY'])

# Prepare template
template_env = Environment(loader=PackageLoader(__name__, 'templates'))
template = template_env.get_template('reminder_email.html')

# Parse member emails into a dict
member_emails = urlparse.parse_qs(env['MEMBER_EMAILS'])

# Querystring parameters
params = {
  'key': env['TRELLO_KEY'],
  'token': env['TRELLO_TOKEN'],
  'fields': 'name,url,dateLastActivity',
  'members': 'true'
}

# Construct trello URL and fetch
url = 'https://api.trello.com/1/boards/%s/cards' % env['TRELLO_BOARD']
r = requests.get(url, params=params)
cards = r.json()

today = arrow.utcnow()
members = {}

# For each card that's older than a week
for card in cards:
  date_last_activity = arrow.get(card[u'dateLastActivity'])
  days_since_activity = abs(today - date_last_activity).days
  if days_since_activity > int(env['MIN_DAYS']):
    # Store days since activity for template
    card[u'days_since_activity'] = days_since_activity
    
    # Add card to each member's list
    for member in card[u'members']:
      username = str(member[u'username'])
      
      try:
        members[username].append(card)
      except KeyError:
        members[username] = [card]

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
      'email': '; '.join(member_emails[username]),
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