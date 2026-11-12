## Lakehouse: Iceberg table + first Spark job

### What is Iceberg and why I used it

Iceberg, in this context, refers to a table format: an organised format for data which are living in a lakehouse. It keeps track of which Parquet files make up the table and keeps a history of every version (snapshots).

The reason I used it is because I am saving my data in a lakehouse, and the reason I am saving data in a lakehouse is because the data I am dealing with are trip logs, which are likely to grow very fast over time, so having them stored raw in a lake is much cheaper. Hence, I need my data organised in the Iceberg format so that my query engines can access them easily for my dashboards.

### How to run it
```bash
uv run python python/iceberg_trips.py
uv run python python/query_iceberg.py
```

- `iceberg_trips.py`: this is for writing (it creates the Iceberg table, one snapshot per month)
- `query_iceberg.py`: this is for reading (it queries the table now and at an older snapshot)

### What I saw (time travel)

| Version | Months in the table | Trips |
|---|---|---|
| Now (snapshot 2) | January + February 2026 | 200,000 |
| Snapshot 1 | January 2026 | 100,000 |

### Spark (local, in Docker)
```bash
docker run -it --rm -p 4040:4040 -v "${PWD}:/work" -w /work apache/spark:4.0.1-python3 /opt/spark/bin/spark-submit python/spark_hello.py
```
Spark is the cleaner, or simply the organiser, of my data which are in the lake. I run it in Docker because it has a lot of dependencies, and I didn't want them to interfere with other programs on my computer. For example:
- Spark needs **Java** (a JDK) installed and set up correctly.
- On Windows, Spark also needs extra **Hadoop files** (`winutils.exe` and `hadoop.dll`) just to write files.
- The **PySpark** and **Python** versions must match the Spark version.

The Docker image already has all of these inside, so it works the same on any computer.

### Warehouse vs lakehouse

Lastly, I learned the difference between a warehouse and a lakehouse. Warehouses receive data that must be structured into tables in the warehouse's own format, but lakehouses receive raw data as they are, as files of any type, and Spark organises them without the need to move them out of the lake.

## Optimizing a slow join

### The problem
In this part I was learning the difference between a sort-merge join (slow join) and a broadcast join.

To understand the problem, first I ran a Python file which split the trips into piles across my CPU cores (the workers). Then, to join the trips with the towns table, Spark used a sort-merge join, where the workers first had to send trips to each other so that all trips of the same town ended up on the same worker, and only then could each worker join its trips with the matching town. But that is slow.

### Why it was slow

At the end of the day, one worker has more trips to join than the others, so they have to wait until the one with a lot of work is done, and this wastes time. Also, a lot of trips have to travel between workers (the shuffle), to ensure that all trips of the same town end up on the same worker.

### The fix

To fix it, a broadcast join is better, because Spark makes a copy of the towns table in the memory of each worker, so the trips don’t have to move, and all workers can join at the same time, and the time is shared equally.

### Before / after
| Join | Best of 3 runs |
|---|---|
| Before: |5.81s|
| After:  |2.05s|

(Speed-up: 2.8X)


### Why the speed-up would be bigger on a real cluster
It would be bigger because the work would be divided across many computers, and sending data through the network takes a long time. For learning, I am just using one machine, with the work divided across my PC’s CPU cores.