#!/usr/bin/env python3
"""Fit an ordinary linear trajectory calibration from a CSV, or run a demo."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calib.solvers.trajectory_linear import (  # noqa: E402
    estimate_trajectory_calibration,
    evaluate_trajectory_calibration,
)

COLUMNS = (
    "road_x_m", "road_y_m", "vehicle_x_m", "vehicle_y_m", "vx_mps", "vy_mps",
)


def load_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
        data = []
        for line, row in enumerate(reader, start=2):
            try:
                data.append([float(row[column]) for column in COLUMNS])
            except (ValueError, TypeError) as error:
                raise ValueError(f"Invalid numeric value on CSV line {line}") from error
    if not data:
        raise ValueError("Input CSV contains no observations")
    data = np.asarray(data, dtype=np.float64)
    return data[:, :2], data[:, 2:4], data[:, 4:6]


def demo_observations():
    """Three synthetic targets with distinct directions and acceleration."""
    road, velocity = [], []
    trajectories = [
        ((-12.0, 4.0), (8.0, 0.0), (0.0, 1.5)),
        ((8.0, -15.0), (0.0, 6.0), (-1.0, 0.0)),
        ((20.0, 12.0), (-5.0, -3.0), (0.4, 0.8)),
    ]
    for origin, speed, acceleration in trajectories:
        origin, speed, acceleration = map(np.asarray, (origin, speed, acceleration))
        for t in np.arange(20) / 10.0:
            road.append(origin + speed * t + 0.5 * acceleration * t ** 2)
            velocity.append(speed + acceleration * t)
    road, velocity = np.asarray(road), np.asarray(velocity)
    yaw, time_offset = np.deg2rad(0.6), 0.04
    rotated = np.column_stack((-road[:, 1], road[:, 0]))
    vehicle = road + [0.8, -0.35] + yaw * rotated + time_offset * velocity
    return road, vehicle, velocity


def export_corrected_csv(path: Path, estimate, observations):
    road, vehicle, velocity = observations
    corrected = estimate.correct(road, velocity)
    distance = np.linalg.norm(vehicle - corrected, axis=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([*COLUMNS, "corrected_road_x_m", "corrected_road_y_m", "residual_distance_m"])
        for row in zip(road, vehicle, velocity, corrected, distance):
            r, v, speed, fixed, error = row
            writer.writerow([*r, *v, *speed, *fixed, error])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Matched observations in CSV format")
    source.add_argument("--demo", action="store_true", help="Run a synthetic, known-parameter example")
    parser.add_argument("--evaluate", type=Path, help="Optional independent evaluation CSV")
    parser.add_argument("--threshold-m", type=float, default=0.5, help="Consistency distance threshold")
    parser.add_argument("--output", type=Path, help="Save the JSON report")
    parser.add_argument("--corrected-output", type=Path, help="Export corrected evaluation observations")
    args = parser.parse_args(argv)
    try:
        fit_data = demo_observations() if args.demo else load_csv(args.input)
        estimate = estimate_trajectory_calibration(*fit_data)
        evaluation_data = load_csv(args.evaluate) if args.evaluate else fit_data
        result = {
            "method": "ordinary_least_squares_linearized_2d_trajectory_residual",
            "model": "p_vehicle - p_road = T + yaw * J*p_road + velocity * time_offset + residual",
            "time_offset_convention": "Positive shifts the road observation along the supplied velocity",
            "estimate": estimate.to_dict(),
            "fit_metrics": evaluate_trajectory_calibration(estimate, *fit_data, threshold_m=args.threshold_m),
            "evaluation": {
                "data_role": "held_out" if args.evaluate else "training_data",
                **evaluate_trajectory_calibration(estimate, *evaluation_data, threshold_m=args.threshold_m),
            },
            "warnings": [],
        }
        if args.demo:
            result["demo_truth"] = {"translation_x_m": 0.8, "translation_y_m": -0.35, "yaw_deg": 0.6, "time_offset_ms": 40.0}
        if estimate.scaled_condition_number > 1e6:
            result["warnings"].append("The normalized design matrix is poorly conditioned; parameter estimates may be unstable.")
        if abs(estimate.yaw_rad) > np.deg2rad(5.0):
            result["warnings"].append("Estimated yaw exceeds 5 degrees; review the small-angle approximation.")
        serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.corrected_output:
            export_corrected_csv(args.corrected_output, estimate, evaluation_data)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
        return 0
    except (ValueError, OSError, np.linalg.LinAlgError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
