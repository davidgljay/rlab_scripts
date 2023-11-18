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
event_id = None

# Connect to Notion
try:
    # Connect to Notion
    notion = Client(auth=os.getenv('NOTION_API_TOKEN'))
    # contacts_table = client.get_collection_view(os.getenv('CONTACTS_DATABASE_ID'))
    # invitations_table = client.get_collection_view(os.getenv('INVITATIONS_DATABASE_ID'))

    # Your other code ...

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
    if (isinstance(row['Phone - This will be used to send brief follow-up surveys after events you attend.'], str)):
        print('Updating phone', row['Phone - This will be used to send brief follow-up surveys after events you attend.'])
        notion.pages.update(
                **{
                    "page_id": page_id,
                    "properties": {
                        "Phone": {
                            "phone_number": row['Phone - This will be used to send brief follow-up surveys after events you attend.'] 
                 
                        }
                    }
                }
            )
    if (isinstance(row['Location'], str)):
        print('updating location')
        notion.pages.update(
                **{
                    "page_id": page_id,
                    "properties": {
                        "Location": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": row['Location']
                                    }
                                }
                            ]
                        }
                    }
                }
            )

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
    print(contact_page_id)

    # Find Invitation Page
    invitation_page_results = notion.databases.query(
            **{
                "database_id": os.getenv('INVITATION_DATABASE_ID'),
                "filter": {
                    "property": "🤵🏽‍♀️ Contacts",
                    "relation": {
                        "contains": contact_page_id,
                    },
                },
            }
        )
    if invitation_page_results:
        invitation_page_id = invitation_page_results['results'][0]['id']
        print(invitation_page_id)
        print(notion_update_invitation(invitation_id, contact_id))


        # Update Status to "Registered"
        print(f"Updated Status for {email} to Registered.")
    else:
        print(f"No Invitation found for {email}.")

# Save changes
client.submit_transaction()