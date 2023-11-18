import pandas as pd
from notion.client import NotionClient

# Notion API Token
NOTION_API_TOKEN = 'your-notion-api-token'
# Notion Database ID for Contacts and Invitations
CONTACTS_DATABASE_ID = 'your-contacts-database-id'
INVITATIONS_DATABASE_ID = 'your-invitations-database-id'

# Read CSV
csv_path = 'your-file.csv'
df = pd.read_csv(csv_path)

# Connect to Notion
client = NotionClient(token_v2=NOTION_API_TOKEN)
contacts_table = client.get_collection_view(CONTACTS_DATABASE_ID)
invitations_table = client.get_collection_view(INVITATIONS_DATABASE_ID)

# Update Notion Tables
for index, row in df.iterrows():
    email = row['email']
    
    # Find Contact Page ID
    contact_page = contacts_table.collection.get_rows(search=email)
    if contact_page:
        contact_page_id = contact_page[0].id

        # Find Invitation Page
        invitation_page = invitations_table.collection.get_rows(search=contact_page_id)
        if invitation_page:
            invitation_page_id = invitation_page[0].id

            # Update Status to "Registered"
            invitation_page[0].status = "Registered"
            print(f"Updated Status for {email} to Registered.")
        else:
            print(f"No Invitation found for {email}.")
    else:
        print(f"No Contact found for {email}.")

# Save changes
client.submit_transaction()