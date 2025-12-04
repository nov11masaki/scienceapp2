
import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

project_id = os.getenv('GCP_PROJECT_ID')
bucket_name = os.getenv('GCS_BUCKET_NAME')

print(f"Project ID: {project_id}")
print(f"Bucket Name: {bucket_name}")

try:
    storage_client = storage.Client(project=project_id)
    print("Client created.")
    
    bucket = storage_client.bucket(bucket_name)
    print(f"Checking if bucket '{bucket_name}' exists...")
    
    if bucket.exists():
        print("Bucket exists!")
        print("Listing blobs...")
        blobs = list(bucket.list_blobs(max_results=5))
        for blob in blobs:
            print(f" - {blob.name}")
    else:
        print("Bucket does not exist.")

except Exception as e:
    print(f"Error: {e}")
