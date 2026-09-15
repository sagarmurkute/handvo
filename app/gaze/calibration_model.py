"""Gaze-to-screen coordinate regression model with Ridge Regularization and bounded prediction."""

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class ModelMetrics:
    """Quality and performance metrics for the fitted calibration model."""

    rmse: float = 0.0
    quality: str = "UNKNOWN"
    sample_count: int = 0
    trained_at: float = 0.0


class CalibrationModel:
    """Ridge-regularized polynomial regression mapping normalized gaze coordinates to screen positions."""

    def __init__(self, degree: int = 2, ridge_alpha: float = 0.015) -> None:
        self.degree = degree
        self.ridge_alpha = ridge_alpha
        self.weights_x: Optional[np.ndarray] = None
        self.weights_y: Optional[np.ndarray] = None
        self.metrics: ModelMetrics = ModelMetrics()
        self.is_trained: bool = False

    def _features(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Construct polynomial feature matrix with numerical stability."""
        x = np.asarray(x).flatten()
        y = np.asarray(y).flatten()
        if self.degree == 2:
            return np.column_stack([np.ones_like(x), x, y, x**2, y**2, x * y])
        return np.column_stack([np.ones_like(x), x, y])

    def fit(self, gaze_pts: List[Tuple[float, float]], target_pts: List[Tuple[float, float]]) -> bool:
        """
        Fit regularized regression weights mapping gaze (x, y) to target screen positions (x, y).

        Args:
            gaze_pts: List of (gaze_x, gaze_y) normalized coordinates.
            target_pts: List of (target_x, target_y) normalized coordinates.

        Returns:
            True if fitting succeeded, False otherwise.
        """
        if len(gaze_pts) < 4 or len(gaze_pts) != len(target_pts):
            self.is_trained = False
            return False

        # If too few points for degree 2, drop to degree 1 (linear/affine)
        if len(gaze_pts) < 6:
            self.degree = 1

        gaze_arr = np.array(gaze_pts, dtype=np.float64)
        target_arr = np.array(target_pts, dtype=np.float64)

        gx, gy = gaze_arr[:, 0], gaze_arr[:, 1]
        tx, ty = target_arr[:, 0], target_arr[:, 1]

        A = self._features(gx, gy)
        n_features = A.shape[1]

        try:
            # Ridge regularization (L2 penalty on higher-order terms to prevent Runge oscillations)
            reg_matrix = np.eye(n_features, dtype=np.float64) * self.ridge_alpha
            reg_matrix[0, 0] = 0.0  # Do not penalize bias intercept

            AtA = A.T @ A + reg_matrix
            At_tx = A.T @ tx
            At_ty = A.T @ ty

            wx = np.linalg.solve(AtA, At_tx)
            wy = np.linalg.solve(AtA, At_ty)

            self.weights_x = wx
            self.weights_y = wy

            # Compute error metrics
            pred_tx = A @ wx
            pred_ty = A @ wy
            residuals = np.sqrt((tx - pred_tx) ** 2 + (ty - pred_ty) ** 2)
            rmse = float(np.mean(residuals))

            # Quality scoring
            if rmse <= 0.08:
                quality = "EXCELLENT"
            elif rmse <= 0.14:
                quality = "GOOD"
            elif rmse <= 0.22:
                quality = "ACCEPTABLE"
            else:
                quality = "NEEDS IMPROVEMENT"

            self.metrics = ModelMetrics(
                rmse=rmse,
                quality=quality,
                sample_count=len(gaze_pts),
                trained_at=time.time(),
            )
            self.is_trained = True
            return True
        except Exception:
            self.is_trained = False
            return False

    def predict(
        self,
        gaze_x: float,
        gaze_y: float,
        screen_w: Optional[int] = None,
        screen_h: Optional[int] = None,
    ) -> Tuple[float, float]:
        """
        Predict calibrated screen coordinate from normalized gaze coordinate.

        Args:
            gaze_x: Normalized horizontal gaze (0.0 to 1.0).
            gaze_y: Normalized vertical gaze (0.0 to 1.0).
            screen_w: Optional pixel width to scale output to pixel coords.
            screen_h: Optional pixel height to scale output to pixel coords.

        Returns:
            (norm_x, norm_y) or (pixel_x, pixel_y) if dimensions provided.
        """
        if not self.is_trained or self.weights_x is None or self.weights_y is None:
            norm_x, norm_y = gaze_x, gaze_y
        else:
            gx = float(np.clip(gaze_x, -0.2, 1.2))
            gy = float(np.clip(gaze_y, -0.2, 1.2))
            feat = self._features(np.array([gx]), np.array([gy]))
            raw_pred_x = float((feat @ self.weights_x)[0])
            raw_pred_y = float((feat @ self.weights_y)[0])

            # Clamp output to normalized display space [0.0, 1.0]
            norm_x = float(np.clip(raw_pred_x, 0.0, 1.0))
            norm_y = float(np.clip(raw_pred_y, 0.0, 1.0))

        if screen_w is not None and screen_h is not None:
            return norm_x * screen_w, norm_y * screen_h

        return norm_x, norm_y

    def save_to_json(self, filepath: str | Path) -> bool:
        """Persist calibration parameters and metrics to a JSON file."""
        if not self.is_trained or self.weights_x is None or self.weights_y is None:
            return False

        data: Dict[str, Any] = {
            "degree": self.degree,
            "weights_x": self.weights_x.tolist(),
            "weights_y": self.weights_y.tolist(),
            "metrics": asdict(self.metrics),
        }

        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def load_from_json(self, filepath: str | Path) -> bool:
        """Load calibration model from a JSON file."""
        path = Path(filepath)
        if not path.exists():
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.degree = data.get("degree", 2)
            self.weights_x = np.array(data["weights_x"])
            self.weights_y = np.array(data["weights_y"])
            metrics_data = data.get("metrics", {})
            self.metrics = ModelMetrics(
                rmse=metrics_data.get("rmse", 0.0),
                quality=metrics_data.get("quality", "UNKNOWN"),
                sample_count=metrics_data.get("sample_count", 0),
                trained_at=metrics_data.get("trained_at", 0.0),
            )
            self.is_trained = True
            return True
        except Exception:
            self.is_trained = False
            return False
