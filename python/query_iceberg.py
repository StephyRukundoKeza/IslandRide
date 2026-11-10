"""Query the IslandRide Iceberg table with DuckDB, now and as it was at the first snapshot (time travel)."""

from pathlib import Path

from pyiceberg.catalog.sql import SqlCatalog

WAREHOUSE = Path("data/lakehouse").resolve()
TABLE = "islandride.trips"

TRIPS_PER_MONTH = """
    SELECT date_trunc('month', requested_at) AS month, count(*) AS trips
    FROM trips
    GROUP BY month
    ORDER BY month
"""


def main():
    catalog = SqlCatalog(
        "local",
        uri=f"sqlite:///{WAREHOUSE / 'catalog.db'}",
        warehouse=WAREHOUSE.as_uri(),
        **{"py-io-impl": "pyiceberg.io.fsspec.FsspecFileIO"},
    )
    table = catalog.load_table(TABLE)

    print("Snapshots (the table's history):")
    for number, snap in enumerate(table.snapshots(), start=1):
        print(
            f"  {number}. id={snap.snapshot_id}  {snap.summary.operation.value}  "
            f"added={snap.summary.get('added-records')}  total={snap.summary.get('total-records')}"
        )

    print("\nThe table NOW (latest snapshot):")
    con = table.scan().to_duckdb(table_name="trips")
    con.sql(TRIPS_PER_MONTH).show()

    first = table.snapshots()[0].snapshot_id
    print(f"TIME TRAVEL: the table as it was at snapshot 1 ({first}):")
    old = table.scan(snapshot_id=first).to_duckdb(table_name="trips")
    old.sql(TRIPS_PER_MONTH).show()


if __name__ == "__main__":
    main()