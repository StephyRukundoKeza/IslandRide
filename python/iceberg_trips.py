"""Load IslandRide's raw Parquet trips into a local Iceberg table, one month per snapshot."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pyiceberg.catalog.sql import SqlCatalog

WAREHOUSE = Path("data/lakehouse").resolve()
RAW_TRIPS = Path("data/raw/trips")
TABLE = "islandride.trips"


def utc_timestamps(table: pa.Table) -> pa.Table:
    """Iceberg stores timezone-aware timestamps in UTC only: relabel them as UTC (same instant)."""
    fields = [
        pa.field(f.name, pa.timestamp(f.type.unit, tz="UTC"), f.nullable)
        if pa.types.is_timestamp(f.type) and f.type.tz
        else f
        for f in table.schema
    ]
    return table.cast(pa.schema(fields))


def main():
    WAREHOUSE.mkdir(parents=True, exist_ok=True)
    catalog = SqlCatalog(
        "local",
        uri=f"sqlite:///{WAREHOUSE / 'catalog.db'}",
        warehouse=WAREHOUSE.as_uri(),
        **{"py-io-impl": "pyiceberg.io.fsspec.FsspecFileIO"},
    )
    catalog.create_namespace_if_not_exists("islandride")

    files = sorted(RAW_TRIPS.glob("year=*/month=*/trips.parquet"))
    if not files:
        raise SystemExit("No trips found. Run generate_trips.py first.")

    if catalog.table_exists(TABLE):
        catalog.drop_table(TABLE)
    first = utc_timestamps(pq.read_table(files[0]))
    table = catalog.create_table(TABLE, schema=first.schema)

    for f in files:
        table.append(utc_timestamps(pq.read_table(f)))
        print(f"appended {f} -> snapshot {table.current_snapshot().snapshot_id}")

    print("rows in table:", len(table.scan().to_arrow()))
    print("snapshots:", len(table.snapshots()))
    print("latest metadata file:", table.metadata_location)


if __name__ == "__main__":
    main()