from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = TableServiceClient(endpoint="https://nakamura-cosmosdb.table.cosmos.azure.com:443/", credential=credential)

table = client.get_table_client("contents")
new_entity = {
    "RowKey": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
    "PartitionKey": "gear-surf-surfboards",
    "Name": "Yamba Surfboard",
    "Quantity": 12,
    "Sale": False,
}
created_entity = table.create_entity(new_entity)
