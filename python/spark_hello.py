"""First PySpark job: read IslandRide's raw trips, see lazy evaluation, write a small Gold table."""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

RAW_TRIPS = "data/raw/trips"
GOLD_OUT = "data/gold/trips_per_month"


def main():
    spark = SparkSession.builder.appName("islandride-hello").master("local[*]").getOrCreate()

    trips = spark.read.parquet(RAW_TRIPS)
    print("Columns:", trips.columns)
    trips.printSchema()

    per_month = trips.groupBy("year", "month").agg(F.count("*").alias("trips")).orderBy("year", "month")

    print("Nothing has run yet. Here is Spark's PLAN (lazy evaluation):")
    per_month.explain()

    print("Now an ACTION (.show) makes Spark actually run:")
    per_month.show()

    per_month.write.mode("overwrite").parquet(GOLD_OUT)
    print(f"Wrote {GOLD_OUT}")

    input("Spark UI is at http://localhost:4040 - press Enter to stop...")
    spark.stop()


if __name__ == "__main__":
    main()