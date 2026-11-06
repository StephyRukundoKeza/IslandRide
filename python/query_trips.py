"""Query the trip Parquet files straight from Azure storage with DuckDB, without downloading them first."""
import os

import duckdb
from dotenv import load_dotenv

load_dotenv()
CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
CONTAINER = os.getenv("RAW_CONTAINER", "raw")

con = duckdb.connect()
con.sql("INSTALL azure; LOAD azure;")
con.execute(f"CREATE SECRET storage (TYPE azure, CONNECTION_STRING '{CONNECTION_STRING}')")

trips = f"read_parquet('az://{CONTAINER}/trips/*/*/*.parquet', hive_partitioning = true)"

print("--- Trips per month (year and month come from the folder names) ---")
print(con.sql(f"""
    SELECT year, month, count(*) AS trips, round(sum(fare_mur)) AS revenue_mur
    FROM {trips}
    GROUP BY year, month
    ORDER BY year, month
"""))

print("--- Busiest pickup towns (completed trips) ---")
print(con.sql(f"""
    SELECT pickup_town, count(*) AS trips, round(avg(fare_mur), 2) AS avg_fare_mur
    FROM {trips}
    WHERE status = 'completed'
    GROUP BY pickup_town
    ORDER BY trips DESC
"""))

print("--- Partition pruning: only October's file is read ---")
print(con.sql(f"SELECT count(*) AS october_trips FROM {trips} WHERE month = 10"))