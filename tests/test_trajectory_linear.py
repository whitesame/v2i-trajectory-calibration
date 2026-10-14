import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from calib.solvers.trajectory_linear import (
    UnobservableCalibrationError,
    estimate_trajectory_calibration,
    evaluate_trajectory_calibration,
)


class TrajectoryCalibrationTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(24)
        self.road = rng.uniform(-40, 40, (600, 2))
        self.velocity = rng.uniform(-15, 15, (600, 2))
        self.truth = np.array([0.8, -0.35, np.deg2rad(0.6), 0.04])
        rotation = np.column_stack((-self.road[:, 1], self.road[:, 0]))
        self.vehicle = (
            self.road + self.truth[:2] + self.truth[2] * rotation
            + self.truth[3] * self.velocity
        )

    def test_recovers_parameters_and_corrects_held_out_data(self):
        model = estimate_trajectory_calibration(self.road[:400], self.vehicle[:400], self.velocity[:400])
        np.testing.assert_allclose(model.parameters, self.truth, atol=1e-12)
        metrics = evaluate_trajectory_calibration(model, self.road[400:], self.vehicle[400:], self.velocity[400:])
        self.assertLess(metrics["after"]["position_rmse_m"], 1e-12)
        self.assertEqual(metrics["after"]["consistency_rate"], 1.0)
        self.assertGreater(metrics["before"]["median_distance_m"], 0.5)

    def test_noise_and_covariance(self):
        noise = np.random.default_rng(7).normal(0, 0.03, self.vehicle.shape)
        model = estimate_trajectory_calibration(self.road, self.vehicle + noise, self.velocity)
        np.testing.assert_allclose(model.parameters[:2], self.truth[:2], atol=0.005)
        np.testing.assert_allclose(model.parameters[2:], self.truth[2:], atol=0.001)
        self.assertEqual(model.covariance.shape, (4, 4))
        np.testing.assert_allclose(model.covariance, model.covariance.T, atol=1e-14)
        self.assertTrue(np.all(np.diag(model.covariance) > 0))

    def test_rejects_constant_velocity_time_translation_coupling(self):
        velocity = np.tile([8.0, 0.0], (len(self.road), 1))
        with self.assertRaises(UnobservableCalibrationError):
            estimate_trajectory_calibration(self.road, self.vehicle, velocity)

    def test_rejects_static_targets(self):
        with self.assertRaises(UnobservableCalibrationError):
            estimate_trajectory_calibration(self.road, self.vehicle, np.zeros_like(self.road))

    def test_validates_shapes_and_finite_data(self):
        with self.assertRaises(ValueError):
            estimate_trajectory_calibration(self.road[:, 0], self.vehicle, self.velocity)
        with self.assertRaises(ValueError):
            estimate_trajectory_calibration(self.road, self.vehicle[:-1], self.velocity)
        invalid = self.road.copy()
        invalid[0, 0] = np.nan
        with self.assertRaises(ValueError):
            estimate_trajectory_calibration(invalid, self.vehicle, self.velocity)

    def test_cli_demo_writes_valid_report_and_corrected_csv(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "estimate.json"
            corrected = Path(directory) / "corrected.csv"
            completed = subprocess.run(
                [sys.executable, str(root / "tools/estimate_trajectory_calibration.py"),
                 "--demo", "--output", str(report), "--corrected-output", str(corrected)],
                cwd=root, capture_output=True, text=True, check=True,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertAlmostEqual(payload["estimate"]["time_offset_ms"], 40.0)
            self.assertEqual(payload["evaluation"]["data_role"], "training_data")
            self.assertEqual(len(corrected.read_text().splitlines()), 61)
            self.assertEqual(payload, json.loads(completed.stdout))

    def test_cli_csv_fits_and_evaluates_distinct_files(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(root / "tools/estimate_trajectory_calibration.py"),
             "--input", str(root / "examples/trajectory_fit.csv"),
             "--evaluate", str(root / "examples/trajectory_holdout.csv")],
            cwd=root, capture_output=True, text=True, check=True,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["evaluation"]["data_role"], "held_out")
        self.assertEqual(payload["estimate"]["sample_count"], 30)
        self.assertEqual(payload["evaluation"]["sample_count"], 30)
        self.assertAlmostEqual(payload["estimate"]["yaw_deg"], 0.6, places=8)
        self.assertLess(payload["evaluation"]["after"]["position_rmse_m"], 1e-10)


if __name__ == "__main__":
    unittest.main()
