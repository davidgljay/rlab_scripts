import sys
import os
import pandas as pd
from notion_client import Client
from dotenv import load_dotenv
from requests.exceptions import HTTPError

#Load environment variables
load_dotenv()

# Read CSV
csv_path = sys.argv[1]
df = pd.read_csv(csv_path)
event_page_id = sys.argv[2]
status="Registered For Event"

# Connect to Notion
try:
    notion = Client(auth=os.getenv('NOTION_API_TOKEN'))

except HTTPError as e:
    print(f"Error connecting to Notion API: {e}")

def notion_create_contact(row):
    return notion.pages.create(
        **{
            "parent": {
                "database_id": os.getenv('CONTACT_DATABASE_ID')
            },
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": row['name']
                            }
                        }
                    ]
                },
                "Email": {
                    "email":  row['email']
                }
            }
        })

def notion_update_contact(row, page_id):
    update_call = {"page_id": page_id, "properties": {}}
    if (isinstance(row['Phone - This will be used to send brief follow-up surveys after events you attend.'], str)):
        update_call['properties']['Phone'] = {"phone_number": row['Phone - This will be used to send brief follow-up surveys after events you attend.']}
    if (isinstance(row['Location'], str)):
        update_call['properties']['Location'] = {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": row['Location']
                                    }
                                }
                            ]
                        }
    return notion.pages.update(**update_call)

def notion_create_invitation(contact_page_id, event_page_id, status):
    return notion.pages.create(
        **{
            "parent": {
                "database_id": os.getenv('INVITATION_DATABASE_ID')
            },
            "properties": {
                "🤵🏽‍♀️ Contacts": {
                    "relation":  [{
                        "id": contact_page_id
                    }]
                },
                "📅 Meeting Notes": {
                    "relation": [{
                        "id": event_page_id
                    }]
                },
                "Status": {
                    "status": {
                        "name": "Registered For Event"
                    }
                }
            }
        })


def notion_update_invitation(invitation_page_id):
    return notion.pages.update(
    **{
        "page_id": invitation_page_id,
        "properties": {
            "Status": {
                "status":  {
                    "name": "Registered For Event"
                }
            }
        }
    }
    )


# Update Notion Tables
for index, row in df.iterrows():
    email = row['email']
    print(email)
    # Find Contact Page ID
    contact_page = notion.databases.query(
            **{
                "database_id": os.getenv('CONTACT_DATABASE_ID'),
                "filter": {
                    "property": "Email",
                    "rich_text": {
                        "contains": email,
                    },
                },
            }
        )
    ## TODO: Make contact record if nothing is found.
    if len(contact_page['results']) == 0:
        print("Creating a contact record for", email)
        contact_page_id= notion_create_contact(row)['id']
    else:
        contact_page_id = contact_page['results'][0]['id']
        print('Updating contact record for', email) 
    notion_update_contact(row, contact_page_id)

    # Find Invitation Page
    invitation_page_results = notion.databases.query(
            **{
                "database_id": os.getenv('INVITATION_DATABASE_ID'),
                "filter": {
                    "and": [
                        {
                            "property": "🤵🏽‍♀️ Contacts",
                            "relation": {
                                "contains": contact_page_id,
                            },
                        },
                        {
                            "property": "📅 Meeting Notes",
                            "relation": {
                                "contains": event_page_id,
                            },
                        },
                    ]
                },
            }
        )
    if not invitation_page_results['results']:
        notion_create_invitation(contact_page_id, event_page_id, status)
    else:
        invitation_page_id = invitation_page_results['results'][0]['id']
        update_invitation_result = notion_update_invitation(invitation_page_id)


        # Update Status to "Registered"
        print(f"Updated Status for {email} to Registered.")
