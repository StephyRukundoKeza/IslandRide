"""Caching (reuse cleaned trips across reports) and data skew (one town much bigger than the others)."""

import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

RAW_TRIPS = "data/raw/trips"


def clean(trips):
    return (
        trips.filter(F.col("status") == "completed")
        .filter(F.col("distance_km") > 0)
        .withColumn("fare_per_km", F.col("fare_mur") / F.col("distance_km"))
    )


def run_reports(df):
    """Three different reports on the same cleaned trips."""
    start = time.perf_counter()
    df.groupBy("pickup_town").count().collect()
    df.groupBy("month").agg(F.sum("fare_mur")).collect()
    df.agg(F.avg("fare_per_km")).collect()
    return time.perf_counter() - start


def main():
    spark = (
        SparkSession.builder.appName("islandride-cache-skew")
        .master("local[*]")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "false")
        .getOrCreate()
    )
    trips = spark.read.parquet(RAW_TRIPS)
    trips.count()  # warm-up: read the files once before timing

    # CACHING
    without_cache = run_reports(clean(trips))
    print(f"3 reports WITHOUT cache: {without_cache:.2f}s  (each report re-reads and re-cleans the raw files)")

    cleaned = clean(trips).cache()
    start = time.perf_counter()
    rows = cleaned.count()  # the first action fills the cache
    print(f"Filling the cache ({rows} rows): {time.perf_counter() - start:.2f}s")

    with_cache = run_reports(cleaned)
    print(f"3 reports WITH cache:    {with_cache:.2f}s  (they read the cleaned trips from memory)")
    print(f"Speed-up for the reports: {without_cache / with_cache:.1f}x")

    # DATA SKEW
    by_town = cleaned.repartition("pickup_town")
    pile_sizes = (
        by_town.groupBy(F.spark_partition_id().alias("pile"))
        .agg(F.count("*").alias("rows"), F.collect_set("pickup_town").alias("towns"))
        .filter(F.col("rows") > 0)
        .orderBy(F.desc("rows"))
    )
    print("\nAfter grouping trips by town, how big is each worker's pile?")
    pile_sizes.show(truncate=False)

    input("Open http://localhost:4040 -> Storage tab (the cache) and Stages tab (the skew). Press Enter to stop...")
    cleaned.unpersist()
    spark.stop()


if __name__ == "__main__":
    main()