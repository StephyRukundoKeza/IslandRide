"""Join 5M IslandRide trips with a small towns table, and see which join strategy Spark chooses."""

import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

RAW_TRIPS = "data/raw/trips"

TOWNS = [
    ("Port Louis", "Port Louis", "city"),
    ("Quatre Bornes", "Plaines Wilhems", "town"),
    ("Curepipe", "Plaines Wilhems", "town"),
    ("Rose Hill", "Plaines Wilhems", "town"),
    ("Vacoas", "Plaines Wilhems", "town"),
    ("Ebene", "Plaines Wilhems", "business hub"),
    ("Grand Baie", "Rivière du Rempart", "coastal"),
    ("Moka", "Moka", "town"),
    ("Pamplemousses", "Pamplemousses", "village"),
    ("Flacq", "Flacq", "village"),
    ("Tamarin", "Black River", "coastal"),
    ("Mahébourg", "Grand Port", "coastal"),
]


def main():
    spark = SparkSession.builder.appName("islandride-joins").master("local[*]").getOrCreate()

    trips = spark.read.parquet(RAW_TRIPS).filter(F.col("status") == "completed")
    towns = spark.createDataFrame(TOWNS, "pickup_town string, district string, area_type string")
    towns.show(truncate=False)

    joined = trips.join(towns, on="pickup_town", how="left")

    unmatched = joined.filter(F.col("district").isNull()).count()
    print("Trips whose town is missing from the towns table:", unmatched)

    by_district = (
        joined.groupBy("district")
        .agg(
            F.count("*").alias("trips"),
            F.sum("fare_mur").cast("long").alias("revenue_mur"),
        )
        .orderBy(F.desc("revenue_mur"))
    )

    print("Spark's plan for the join (look for the word 'Join'):")
    by_district.explain()

    start = time.perf_counter()
    by_district.show(truncate=False)
    print(f"Join + aggregation took {time.perf_counter() - start:.1f}s")

    spark.stop()


if __name__ == "__main__":
    main()