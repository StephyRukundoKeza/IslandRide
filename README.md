# IslandRide

IslandRide is a project used to learn how to build batch and streaming data pipelines with Spark, Kafka/Redpanda and Azure storage, based on ride-hailing trips across Mauritius. The trip data is synthetic, generated with real Mauritian towns and coordinates.

## Object storage: Azurite locally, ADLS Gen2 in the cloud
- `python/generate_trips.py` generates trips as partitioned Parquet (`trips/year=2026/month=10/`), with more trips in busy towns like Port Louis (data skew).
- `python/upload_to_storage.py` uploads them to Azure storage with the Azure SDK.
- `python/query_trips.py` queries them straight from storage with DuckDB, with partition pruning.
- The same code runs against Azurite (local, free) and a real ADLS Gen2 account (Azure for Students); only the connection string in `.env` changes.
- On ADLS Gen2, I added a lifecycle rule: raw trips move to cool storage after 30 days and are deleted after 365 days. I deleted the resource group afterwards to keep costs at zero.

While using Azurite, and ADLS Gen2 with my free student account, I realised that Azurite is used for development, for instance when one wants to run tests locally, while ADLS Gen2 is the one to be used for production.

I also realised how simple it is to switch between Azurite and ADLS Gen2: only one string had to be changed in my `.env` file.

## Local tools vs the cloud

| Local tool | Azure | AWS | Google Cloud |
|---|---|---|---|
| Azurite | ADLS Gen2 / Blob Storage | S3 | Cloud Storage |
| DuckDB | Synapse / Fabric | Redshift | BigQuery |
| Airflow | Data Factory / managed Airflow | MWAA | Cloud Composer |
| Docker | Container Apps | ECS | Cloud Run |
| Spark | Azure Databricks | EMR / Databricks | Dataproc / Databricks |

## How to run
1. Copy `.env.example` to `.env` and paste Azurite's development connection string (from Microsoft's Azurite docs)
2. `docker compose up -d` (Azurite)
3. `uv sync`
4. `uv run python/generate_trips.py --month 9 --seed 9` and `uv run python/generate_trips.py --month 10`
5. `uv run python/upload_to_storage.py`
6. `uv run python/query_trips.py`