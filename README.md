# Trello Reminder
Checks a trello board for cards that haven't been updated in 7 days and emails its members a reminder digest

## Installation
`pip install -r requirements.txt`

## Usage
Copy `.env.sample` to `.env` and fill in the environment variables. Copy `members.yaml.sample` to `members.yaml` and fill in usernames
and email addresses. Then run: 

`python main.py` 