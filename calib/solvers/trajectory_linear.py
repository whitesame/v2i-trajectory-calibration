"""Ordinary least-squares calibration from matched 2D trajectory observations.

All positions and velocities must already use the same horizontal coordinate
frame. For each matched observation the small-angle model is

    p_vehicle - p_road = T + yaw * J @ p_road + velocity * time_offset + error

where J rotates a vector by +90 degrees. A positive time offset shifts the road
observation along the supplied velocity. This module estimates four scalars:
Tx/Ty in metres, yaw in radians, and time offset in seconds.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class UnobservableCalibrationError(ValueError):
    """The observations cannot independently determine all four parameters."""


def _xy(values, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError(f"{name} must have shape (N, 2)")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains NaN or infinite values")
    return array


def _observations(road_xy, vehicle_xy, velocity_xy):
    road = _xy(road_xy, "road_xy")
    vehicle = _xy(vehicle_xy, "vehicle_xy")
    velocity = _xy(velocity_xy, "velocity_xy")
    if road.shape != vehicle.shape or road.shape != velocity.shape:
        raise ValueError("Positions and velocities must have matching (N, 2) shapes")
    if len(road) == 0:
        raise ValueError("At least one matched observation is required")
    return road, vehicle, velocity


def design_matrix(road_xy, velocity_xy) -> np.ndarray:
    """Build the stacked 2N x 4 matrix [I2, J p_road, velocity]."""
    road = _xy(road_xy, "road_xy")
    velocity = _xy(velocity_xy, "velocity_xy")
    if road.shape != velocity.shape:
        raise ValueError("road_xy and velocity_xy must have matching shapes")
    matrix = np.zeros((2 * len(road), 4), dtype=np.float64)
    matrix[0::2, 0] = 1.0
    matrix[1::2, 1] = 1.0
    matrix[0::2, 2] = -road[:, 1]
    matrix[1::2, 2] = road[:, 0]
    matrix[:, 3] = velocity.reshape(-1)
    return matrix


@dataclass(frozen=True)
class TrajectoryCalibration:
    translation_m: np.ndarray
    yaw_rad: float
    time_offset_s: float
    sample_count: int
    rank: int
    scaled_condition_number: float
    residuals_m: np.ndarray
    covariance: np.ndarray | None

    @property
    def parameters(self) -> np.ndarray:
        return np.array([
            self.translation_m[0], self.translation_m[1],
            self.yaw_rad, self.time_offset_s,
        ])

    def correct(self, road_xy, velocity_xy) -> np.ndarray:
        """Apply the same linearized model; this is not future prediction."""
        road = _xy(road_xy, "road_xy")
        correction = (design_matrix(road, velocity_xy) @ self.parameters).reshape(-1, 2)
        return road + correction

    def to_dict(self) -> dict:
        standard_deviations = None
        if self.covariance is not None:
            sd = np.sqrt(np.maximum(np.diag(self.covariance), 0.0))
            standard_deviations = {
                "translation_x_m": float(sd[0]), "translation_y_m": float(sd[1]),
                "yaw_rad": float(sd[2]), "time_offset_s": float(sd[3]),
            }
        return {
            "translation_x_m": float(self.translation_m[0]),
            "translation_y_m": float(self.translation_m[1]),
            "yaw_rad": self.yaw_rad,
            "yaw_deg": float(np.rad2deg(self.yaw_rad)),
            "time_offset_s": self.time_offset_s,
            "time_offset_ms": 1000.0 * self.time_offset_s,
            "sample_count": self.sample_count,
            "design_matrix_rank": self.rank,
            "column_normalized_condition_number": self.scaled_condition_number,
            "parameter_order": ["translation_x_m", "translation_y_m", "yaw_rad", "time_offset_s"],
            "covariance": None if self.covariance is None else self.covariance.tolist(),
            "standard_deviations": standard_deviations,
        }


def estimate_trajectory_calibration(road_xy, vehicle_xy, velocity_xy) -> TrajectoryCalibration:
    """Estimate the four parameters by ordinary (unweighted) least squares.

    Column normalization improves numerical scaling without changing the
    objective. Rank-deficient data are rejected rather than reported as a
    uniquely identifiable calibration. Covariance uses the iid, equal-variance
    residual model and is unavailable when there are no residual degrees of
    freedom. It does not include association or errors-in-variables uncertainty.
    """
    road, vehicle, velocity = _observations(road_xy, vehicle_xy, velocity_xy)
    if len(road) < 2:
        raise ValueError("At least two matched observations are required for fitting")
    matrix = design_matrix(road, velocity)
    target = (vehicle - road).reshape(-1)
    scales = np.linalg.norm(matrix, axis=0)
    scales[scales == 0.0] = 1.0
    normalized = matrix / scales
    scaled_parameters, _, rank, singular_values = np.linalg.lstsq(normalized, target, rcond=None)
    if rank < 4:
        raise UnobservableCalibrationError(
            f"Design matrix rank is {rank}/4: translation, yaw and time offset "
            "cannot be estimated independently. Include diverse target velocities "
            "and positions; static or identical-velocity tracks are insufficient."
        )
    parameters = scaled_parameters / scales
    residual_vector = target - matrix @ parameters
    degrees_of_freedom = len(target) - 4
    covariance = None
    if degrees_of_freedom > 0:
        sigma_squared = float(residual_vector @ residual_vector) / degrees_of_freedom
        inverse = np.linalg.pinv(normalized) / scales[:, None]
        covariance = sigma_squared * (inverse @ inverse.T)
    return TrajectoryCalibration(
        translation_m=parameters[:2], yaw_rad=float(parameters[2]),
        time_offset_s=float(parameters[3]), sample_count=len(road), rank=int(rank),
        scaled_condition_number=float(singular_values[0] / singular_values[-1]),
        residuals_m=residual_vector.reshape(-1, 2), covariance=covariance,
    )


def evaluate_trajectory_calibration(
    estimate: TrajectoryCalibration, road_xy, vehicle_xy, velocity_xy,
    threshold_m: float = 0.5,
) -> dict:
    """Compare matched-position distances before and after correction."""
    if not np.isfinite(threshold_m) or threshold_m <= 0:
        raise ValueError("threshold_m must be finite and positive")
    road, vehicle, velocity = _observations(road_xy, vehicle_xy, velocity_xy)
    corrected = estimate.correct(road, velocity)

    def summary(residual):
        distance = np.linalg.norm(residual, axis=1)
        return {
            "position_rmse_m": float(np.sqrt(np.mean(distance ** 2))),
            "median_distance_m": float(np.median(distance)),
            "p90_distance_m": float(np.percentile(distance, 90)),
            "consistency_rate": float(np.mean(distance <= threshold_m)),
        }

    return {
        "sample_count": len(road), "consistency_threshold_m": float(threshold_m),
        "before": summary(vehicle - road),
        "after": summary(vehicle - corrected),
    }
