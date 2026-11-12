"""Optimize a slow join: the same trips + towns join, timed as a sort-merge join (before) and a broadcast join (after)."""

import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

RAW_TRIPS = "data/raw/trips"
RUNS = 3

TOWNS = [
    ("Port Louis", "Port Louis"), ("Quatre Bornes", "Plaines Wilhems"), ("Curepipe", "Plaines Wilhems"),
    ("Rose Hill", "Plaines Wilhems"), ("Vacoas", "Plaines Wilhems"), ("Ebene", "Plaines Wilhems"),
    ("Grand Baie", "Rivière du Rempart"), ("Moka", "Moka"), ("Pamplemousses", "Pamplemousses"),
    ("Flacq", "Flacq"), ("Tamarin", "Black River"), ("Mahébourg", "Grand Port"),
]


def revenue_by_district(trips, towns):
    return (
        trips.join(towns, on="pickup_town", how="left")
        .groupBy("district")
        .agg(F.count("*").alias("trips"), F.sum("fare_mur").cast("long").alias("revenue_mur"))
    )


def join_strategy(df):
    plan = df._jdf.queryExecution().executedPlan().toString()
    for name in ("BroadcastHashJoin", "SortMergeJoin", "ShuffledHashJoin"):
        if name in plan:
            return name
    return "unknown"


def best_time(make_df, label):
    times = []
    for run in range(1, RUNS + 1):
        df = make_df()
        start = time.perf_counter()
        df.collect()
        times.append(time.perf_counter() - start)
        print(f"  {label} run {run}: {times[-1]:.2f}s")
    return min(times)


def main():
    spark = (
        SparkSession.builder.appName("islandride-join-tuning")
        .master("local[*]")
        .config("spark.sql.autoBroadcastJoinThreshold", "-1")
        .config("spark.sql.adaptive.enabled", "false")
        .getOrCreate()
    )

    trips = spark.read.parquet(RAW_TRIPS).filter(F.col("status") == "completed")
    towns = spark.createDataFrame(TOWNS, "pickup_town string, district string")
    print("Completed trips:", trips.count())
    trips.groupBy("pickup_town").count().collect()

    slow = revenue_by_district(trips, towns)
    print("\nBEFORE:", join_strategy(slow), "(both tables are shuffled by town)")
    before = best_time(lambda: revenue_by_district(trips, towns), "sort-merge")

    fast = revenue_by_district(trips, F.broadcast(towns))
    print("\nAFTER:", join_strategy(fast), "(the 12-row towns table is copied to every worker)")
    after = best_time(lambda: revenue_by_district(trips, F.broadcast(towns)), "broadcast")

    print(f"\nBest time BEFORE (sort-merge join): {before:.2f}s")
    print(f"Best time AFTER  (broadcast join):  {after:.2f}s")
    print(f"Speed-up: {before / after:.1f}x")
    fast.orderBy(F.desc("revenue_mur")).show(truncate=False)

    input("Open http://localhost:4040 -> SQL / DataFrame tab to compare both plans. Press Enter to stop...")
    spark.stop()


if __name__ == "__main__":
    main()