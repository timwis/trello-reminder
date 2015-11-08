import os
from os.path import join, dirname
from dotenv import load_dotenv
from urllib import urlencode
import json
import urllib2
from datetime import datetime
import dateutil.parser
import pytz
import mandrill
from jinja2 import Environment, PackageLoader

# Load environment variables
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MIN_DAYS = os.environ.get("MIN_DAYS")
TRELLO_KEY = os.environ.get("TRELLO_KEY")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN")
TRELLO_BOARD = os.environ.get("TRELLO_BOARD")
MANDRILL_KEY = os.environ.get("MANDRILL_KEY")
MSG_FROM_EMAIL = os.environ.get("MSG_FROM_EMAIL")
MSG_FROM_NAME = os.environ.get("MSG_FROM_NAME")
MSG_SUBJECT = os.environ.get("MSG_SUBJECT")
MEMBER_EMAILS = os.environ.get("MEMBER_EMAILS")

mandrill_client = mandrill.Mandrill(MANDRILL_KEY)

# Prepare template
template_env = Environment(loader=PackageLoader(__name__, "templates"))
template = template_env.get_template("reminder_email.html")
			
# Split member emails into a dict
member_emails = {}
member_email_lines = MEMBER_EMAILS.split(",")
for member_email_line in member_email_lines:
	member_email_line_parts = member_email_line.split(":")
	member_emails[member_email_line_parts[0].strip()] = member_email_line_parts[1].strip()

# Querystring parameters
params = {
	"key": TRELLO_KEY,
	"token": TRELLO_TOKEN,
	"fields": "name,url,dateLastActivity",
	"members": "true"
}

# Construct trello URL and fetch
url = "https://api.trello.com/1/boards/" + TRELLO_BOARD + "/cards?" + urlencode(params)
cards = json.load(urllib2.urlopen(url))

today = datetime.now(pytz.utc)
members = {}

# For each card that's older than a week
for card in cards:
	dateLastActivity = dateutil.parser.parse(card[u'dateLastActivity'])
	if abs(today - dateLastActivity).days > int(MIN_DAYS):
		# Add card to each member's list
		for member in card[u'members']:
			username = str(member[u'username'])
			if username not in members:
				members[username] = []
			members[username].append(card)

# For each member
for username in members:
	if username in member_emails:
		# Build message data
		message = {
			"subject": MSG_SUBJECT,
			"from_email": MSG_FROM_EMAIL,
			"from_name": MSG_FROM_NAME or MSG_FROM_EMAIL,
			"to": [{
				"email": member_emails[username],
				"name": username,
				"type": "to"
			}],
			# Construct HTML from template
			"html": template.render(num_days=MIN_DAYS, cards=members[username])
		}
		
		# Send email
		try:
			result = mandrill_client.messages.send(message=message)
			print result
		except mandrill.Error, e:
			print 'A mandrill error occurred: %s - %s' % (e.__class__, e)
			raise