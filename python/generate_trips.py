"""Generate fake IslandRide trips (ride-hailing in Mauritius) and save them as partitioned Parquet."""
import argparse
import calendar
from pathlib import Path

import numpy as np
import pandas as pd

# town: (latitude, longitude, demand weight). Busier towns get more trips, which creates realistic skew.
TOWNS = {
    "Port Louis": (-20.1609, 57.5012, 30),
    "Quatre Bornes": (-20.2654, 57.4791, 12),
    "Curepipe": (-20.3163, 57.5259, 10),
    "Rose Hill": (-20.2400, 57.4700, 9),
    "Vacoas": (-20.2981, 57.4783, 8),
    "Ebene": (-20.2440, 57.4910, 8),
    "Grand Baie": (-20.0094, 57.5807, 7),
    "Moka": (-20.2333, 57.5333, 5),
    "Pamplemousses": (-20.1036, 57.5703, 4),
    "Flacq": (-20.1897, 57.7144, 3),
    "Mahébourg": (-20.4081, 57.7000, 2),
    "Tamarin": (-20.3256, 57.3708, 2),
}
PAYMENT_TYPES = ["cash", "card", "mobile_money"]
BASE_FARE_MUR = 75
PRICE_PER_KM_MUR = 28


def haversine_km(lat1, lon1, lat2, lon2):
    """Straight-line distance between two points on Earth, in km."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def generate(rows: int, year: int, month: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    names = np.array(list(TOWNS))
    weights = np.array([t[2] for t in TOWNS.values()], dtype=float)
    weights /= weights.sum()
    lat = {name: t[0] for name, t in TOWNS.items()}
    lon = {name: t[1] for name, t in TOWNS.items()}

    pickup = rng.choice(names, size=rows, p=weights)
    other_town = rng.choice(names, size=rows, p=weights)
    dropoff = np.where(rng.random(rows) < 0.6, pickup, other_town)   # 60% of trips stay in town

    pickup_lat = pd.Series(pickup).map(lat).to_numpy() + rng.normal(0, 0.01, rows)
    pickup_lon = pd.Series(pickup).map(lon).to_numpy() + rng.normal(0, 0.01, rows)
    dropoff_lat = pd.Series(dropoff).map(lat).to_numpy() + rng.normal(0, 0.01, rows)
    dropoff_lon = pd.Series(dropoff).map(lon).to_numpy() + rng.normal(0, 0.01, rows)

    road_km = haversine_km(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon) * 1.3   # roads aren't straight
    distance_km = np.round(np.maximum(road_km, rng.uniform(1, 6, rows)), 2)
    speed_kmh = rng.uniform(20, 40, rows)
    duration_min = np.round(distance_km / speed_kmh * 60 + rng.uniform(2, 8, rows), 1)

    surge = np.where(rng.random(rows) < 0.1, 1.2, 1.0)                 # 10% of trips at busy times
    fare_mur = np.round((BASE_FARE_MUR + PRICE_PER_KM_MUR * distance_km) * surge)
    status = np.where(rng.random(rows) < 0.92, "completed", "cancelled")
    fare_mur = np.where(status == "completed", fare_mur, 0)

    month_start = pd.Timestamp(year=year, month=month, day=1, tz="Indian/Mauritius")
    seconds_in_month = calendar.monthrange(year, month)[1] * 24 * 3600
    requested_at = month_start + pd.to_timedelta(rng.integers(0, seconds_in_month, rows), unit="s")

    return pd.DataFrame({
        "trip_id": [f"T{year}{month:02d}{i:07d}" for i in range(1, rows + 1)],
        "requested_at": requested_at,
        "rider_id": rng.integers(1, 20_001, rows),
        "driver_id": rng.integers(1, 1_501, rows),
        "pickup_town": pickup,
        "dropoff_town": dropoff,
        "pickup_lat": np.round(pickup_lat, 5),
        "pickup_lon": np.round(pickup_lon, 5),
        "dropoff_lat": np.round(dropoff_lat, 5),
        "dropoff_lon": np.round(dropoff_lon, 5),
        "distance_km": distance_km,
        "duration_min": duration_min,
        "fare_mur": fare_mur,
        "payment_type": rng.choice(PAYMENT_TYPES, size=rows, p=[0.45, 0.35, 0.20]),
        "status": status,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    trips = generate(args.rows, args.year, args.month, args.seed)
    out_dir = Path("data/raw/trips") / f"year={args.year}" / f"month={args.month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    trips.to_parquet(out_dir / "trips.parquet", index=False)
    print(f"Saved {len(trips):,} trips to {out_dir / 'trips.parquet'}")


if __name__ == "__main__":
    main()