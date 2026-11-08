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

## Infrastructure as Code (Terraform)

Instead of creating storage by clicking in the portal, the infrastructure for IslandRide is written as code with Terraform. That means I can create it, destroy it, and recreate it exactly the same way with a few commands.

### What Terraform creates

| Folder | Provider | Resources |
|---|---|---|
| `terraform/local` | Docker (`kreuzwerker/docker`) | Azurite image, a Docker volume, and the Azurite container on port 10000 |
| `terraform/azure` | Azure (`hashicorp/azurerm`) | Resource group `rg-islandride-tf`, an ADLS Gen2 storage account (hierarchical namespace on), `bronze` / `silver` / `gold` containers, and a lifecycle rule (cool after 30 days, delete after 365) |

### Run locally (Docker + Azurite)

Docker Desktop must be running.

```bash
cd terraform/local
terraform init
terraform plan
terraform apply
```

Then upload and query the trips as usual:

```bash
cd ../..
uv run python python/upload_to_storage.py
uv run python python/query_trips.py
```

To remove everything: `terraform destroy`.

### Run on Azure

You need the Azure CLI and to be signed in (`az login`).

```bash
cd terraform/azure
cp terraform.tfvars.example terraform.tfvars   # then put your subscription ID inside
terraform init
terraform plan
terraform apply
terraform output
```

When done, destroy it so it doesn't use credit:

```bash
terraform destroy
```

### What I learned

- **Plan before apply:** `terraform plan` shows exactly what will be created, changed or destroyed before anything happens.
- **State:** Terraform remembers what it created in `terraform.tfstate`. That file contains secrets (like the storage connection string), so it is never committed. Neither is `terraform.tfvars`.
- **Destroy and recreate:** I destroyed both setups and recreated them with one command. The only difference on Azure was a new random suffix on the storage account name, because storage account names must be globally unique.

## Query costs in a warehouse (BigQuery sandbox)

I used the free BigQuery sandbox with public datasets to compare how many bytes different queries read.

| Query | Table | Partitioned? | What it does | Bytes processed |
|---|---|---|---|---|
| 1 | austin_bikeshare.bikeshare_trips | No | 2 columns, all rows | 84.6 MB |
| 2 | austin_bikeshare.bikeshare_trips | No | 2 columns, filter by one day | 106.85 MB |
| 3 | google_trends.top_terms | Yes (`refresh_date`) | no partition filter (estimate only) | 1+ GB |
| 4 | google_trends.top_terms | Yes (`refresh_date`) | filter on one partition | 48 MB |
| 5 | austin_bikeshare.bikeshare_trips | No | `SELECT *` + `LIMIT 10` | 317.26 MB |
| 6 | austin_bikeshare.bikeshare_trips | No | 1 column | 22.25 MB |

So after learning how to query data in a warehouse (BigQuery), I realised something important. One should pay attention to the type of queries they make, because BigQuery bills depending on how many bytes the query reads. For instance, I learned that using `SELECT *` makes the bill go up, and adding `LIMIT` doesn't make it go down. Instead, choosing only the columns I need, and filtering on a partitioned column so fewer rows are read, is what helps.