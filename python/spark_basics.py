"""PySpark DataFrame basics on IslandRide trips, with an incremental Gold table (only new months are processed)."""

import argparse
import time

from pyspark.errors import AnalysisException
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

RAW_TRIPS = "data/raw/trips"
GOLD_TOWN_MONTH = "data/gold/trips_by_town_month"


def months_already_in_gold(spark):
    """The watermark: which (year, month) partitions the Gold table already has."""
    try:
        rows = spark.read.parquet(GOLD_TOWN_MONTH).select("year", "month").distinct().collect()
    except AnalysisException:
        return set()
    return {(r.year, r.month) for r in rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-refresh", action="store_true", help="Rebuild every month, not only new ones")
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("islandride-basics")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "Indian/Mauritius")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .getOrCreate()
    )

    # READ
    trips = spark.read.parquet(RAW_TRIPS)
    print("Rows in raw:", trips.count())
    print("Spark partitions (piles):", trips.rdd.getNumPartitions())

    # INCREMENTAL: find the months that are in raw but not yet in Gold
    raw_months = {(r.year, r.month) for r in trips.select("year", "month").distinct().collect()}
    done = set() if args.full_refresh else months_already_in_gold(spark)
    new_months = sorted(raw_months - done)
    print("Months already in Gold:", sorted(done))
    print("Months to process now:", new_months)
    if not new_months:
        print("Nothing new to process.")
        spark.stop()
        return

    month_filter = F.lit(False)
    for year, month in new_months:
        month_filter = month_filter | ((F.col("year") == year) & (F.col("month") == month))
    new_trips = trips.filter(month_filter)

    # TRANSFORMATIONS (nothing runs yet)
    completed = (
        new_trips.filter(F.col("status") == "completed")
        .withColumn("fare_per_km", F.round(F.try_divide(F.col("fare_mur"), F.col("distance_km")), 2))
        .select("trip_id", "requested_at", "year", "month", "pickup_town", "distance_km", "fare_mur", "fare_per_km")
    )

    # ACTION
    completed.show(5, truncate=False)

    # AGGREGATION
    by_town_month = completed.groupBy("year", "month", "pickup_town").agg(
        F.count("*").alias("trips"),
        F.round(F.avg("fare_mur"), 2).alias("avg_fare_mur"),
        F.round(F.sum("fare_mur"), 0).alias("revenue_mur"),
    )
    start = time.perf_counter()
    by_town_month.orderBy("year", "month", F.desc("trips")).show(20)
    print(f"Aggregation took {time.perf_counter() - start:.1f}s")

    # SPARK SQL (same data, written as SQL)
    new_trips.createOrReplaceTempView("new_trips")
    spark.sql("""
        SELECT year, month, status, count(*) AS trips
        FROM new_trips
        GROUP BY year, month, status
        ORDER BY year, month, status
    """).show(20)

    # WRITE: only the new month folders are written; existing months are left alone
    by_town_month.write.mode("overwrite").partitionBy("year", "month").parquet(GOLD_TOWN_MONTH)
    print(f"Wrote {len(new_months)} month(s) to {GOLD_TOWN_MONTH}")

    spark.stop()


if __name__ == "__main__":
    main()