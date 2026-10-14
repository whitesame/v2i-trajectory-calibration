#!/usr/bin/env python3
"""Regenerate the checked-in known-parameter trajectory CSV examples."""

import csv
from pathlib import Path

from estimate_trajectory_calibration import COLUMNS, demo_observations


def main():
    destination = Path(__file__).resolve().parents[1] / "examples"
    destination.mkdir(parents=True, exist_ok=True)
    road, vehicle, velocity = demo_observations()
    for name, start, end in (("trajectory_fit.csv", 0, 10), ("trajectory_holdout.csv", 10, 20)):
        with (destination / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow([*COLUMNS, "target_id", "timestamp_s"])
            for index, (r, v, speed) in enumerate(zip(road, vehicle, velocity)):
                frame = index % 20
                if start <= frame < end:
                    writer.writerow([
                        *(f"{value:.12f}" for value in (*r, *v, *speed)),
                        index // 20, f"{frame / 10:.1f}",
                    ])
    print(f"Generated trajectory_fit.csv and trajectory_holdout.csv in {destination}")


if __name__ == "__main__":
    main()
