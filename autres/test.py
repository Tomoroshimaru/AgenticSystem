from notion_client import Client

# Initialise correctement le client Notion
client = Client(
    auth="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",
    notion_version="2022-06-28"
)

# Appel API avec le bon ID
resp = client.databases.retrieve("29cf44e4-b545-80d4-8cda-eda58bf4aee2")

# Affiche les propriétés
print(resp["properties"])
