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

# Connect to Notion
try:
    # Connect to Notion
    notion = Client(auth=os.getenv('NOTION_API_TOKEN'))
    # contacts_table = client.get_collection_view(os.getenv('CONTACTS_DATABASE_ID'))
    # invitations_table = client.get_collection_view(os.getenv('INVITATIONS_DATABASE_ID'))

    # Your other code ...

except HTTPError as e:
    print(f"Error connecting to Notion API: {e}")

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
    if contact_page:
        contact_page_id = contact_page['results'][0]['id']
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

            notion.pages.update(
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

            # Update Status to "Registered"
            print(f"Updated Status for {email} to Registered.")
        else:
            print(f"No Invitation found for {email}.")
    else:
        print(f"No Contact found for {email}.")

# Save changes
client.submit_transaction()