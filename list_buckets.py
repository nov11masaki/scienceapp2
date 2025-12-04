
import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

project_id = os.getenv('GCP_PROJECT_ID')

print(f"Project ID: {project_id}")

try:
    storage_client = storage.Client(project=project_id)
    print("Listing buckets in project...")
    buckets = list(storage_client.list_buckets())
    for b in buckets:
        print(f" - {b.name}")
    
    if not buckets:
        print("No buckets found.")

except Exception as e:
    print(f"Error: {e}")
