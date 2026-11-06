"""Upload local Parquet files to Azure storage (Azurite locally, ADLS Gen2 in the cloud), keeping the partitioned paths."""
import os
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()
CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
CONTAINER = os.getenv("RAW_CONTAINER", "raw")
LOCAL_DIR = Path("data/raw")

service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
try:
    service.create_container(CONTAINER)
    print(f"Created container '{CONTAINER}'")
except ResourceExistsError:
    print(f"Container '{CONTAINER}' already exists")

container = service.get_container_client(CONTAINER)
for path in sorted(LOCAL_DIR.rglob("*.parquet")):
    blob_name = path.relative_to(LOCAL_DIR).as_posix()     # e.g. trips/year=2026/month=10/trips.parquet
    with path.open("rb") as file:
        container.upload_blob(blob_name, file, overwrite=True)
    print(f"Uploaded {blob_name} ({path.stat().st_size / 1_000_000:.1f} MB)")

print("\nNow in storage:")
for blob in container.list_blobs():
    print(f"  {CONTAINER}/{blob.name}")