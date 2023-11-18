import sys
import os
import pandas as pd
from notion_client import Client
from dotenv import load_dotenv
from requests.exceptions import HTTPError

# Read CSV
csv_path = sys.argv[1]
df = pd.read_csv(csv_path)

# Connect to Notion
try:
    # Connect to Notion
    client = Client(auth=os.getenv('NOTION_API_TOKEN'))
    contacts_table = client.get_collection_view(os.getenv('CONTACTS_DATABASE_ID'))
    invitations_table = client.get_collection_view(os.getenv('CONTACTS_DATABASE_ID'))

    # Your other code ...

except HTTPError as e:
    print(f"Error connecting to Notion API: {e}")

# Update Notion Tables
for index, row in df.iterrows():
    email = row['email']
    print(email)
    # Find Contact Page ID
    contact_page = contacts_table.collection.get_rows(search=email)
    if contact_page:
        contact_page_id = contact_page[0].id
        print(contact_page_id)

        # Find Invitation Page
        invitation_page = invitations_table.collection.get_rows(search=contact_page_id)
        if invitation_page:
            invitation_page_id = invitation_page[0].id
            print(invitation_page_id)

            # Update Status to "Registered"
            invitation_page[0].status = "Registered"
            print(f"Updated Status for {email} to Registered.")
        else:
            print(f"No Invitation found for {email}.")
    else:
        print(f"No Contact found for {email}.")

# Save changes
client.submit_transaction()