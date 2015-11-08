import pprint
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

# Load environment variables
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TRELLO_KEY = os.environ.get("TRELLO_KEY")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN")
TRELLO_BOARD = os.environ.get("TRELLO_BOARD")
MANDRILL_KEY = os.environ.get("MANDRILL_KEY")
MSG_FROM_EMAIL = os.environ.get("MSG_FROM_EMAIL")
MSG_SUBJECT = os.environ.get("MSG_SUBJECT")

pp = pprint.PrettyPrinter(indent=2)
mandrill_client = mandrill.Mandrill(MANDRILL_KEY)

# Querystring parameters
params = {
	"key": TRELLO_KEY,
	"token": TRELLO_TOKEN,
	"fields": "name,url,dateLastActivity",
	"members": "true"
}

message_template = {
	"subject": MSG_SUBJECT,
	"from_email": MSG_FROM_EMAIL,
	"to": []
}

# Construct URL and fetch
url = "https://api.trello.com/1/boards/" + TRELLO_BOARD + "/cards?" + urlencode(params)
cards = json.load(urllib2.urlopen(url))

today = datetime.now(pytz.utc)
members = {}

# For each card that's older than a week
for card in cards:
	dateLastActivity = dateutil.parser.parse(card[u'dateLastActivity']) 
	if abs(today - dateLastActivity).days > 7:
		# Add card to each member's list
		for member in card[u'members']:
			username = str(member[u'username'])
			if username not in members:
				members[username] = []
			members[username].append(card)
			
# Load member email addresses from json file
with open("members.json") as members_file:
	member_emails = json.load(members_file)
	
for username in members:
	if username in member_emails:
		print member_emails[username]
		
		# Add member-specific info to message template
		message = message_template.copy()
		message["to"].append({
			"email": member_emails[username],
			"name": username,
			"type": "to"
		})
		
		# Add markup for each card to an array
		member_cards = []
		for card in members[username]:
			member_cards.append("<li><a href=\"" + card[u'url'] + "\">" + card[u'name'] + "</a></li>")
		
		# Construct HTML
		message["html"] = "The following cards haven't been updated in over 7 days:<br><ul>" + "\n".join(member_cards) + "</ul>"
		
		# Send email
		try:
			result = mandrill_client.messages.send(message=message)
			print result
		except mandrill.Error, e:
			print 'A mandrill error occurred: %s - %s' % (e.__class__, e)
			raise