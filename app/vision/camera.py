"""Webcam capture engine using OpenCV."""

import sys
from typing import Optional, Tuple
import cv2
import numpy as np


class Camera:
    """Manages OpenCV video capture lifecycle with mirror reflection."""

    def __init__(self, device_index: int = 0, mirror: bool = True) -> None:
        self.device_index = device_index
        self.mirror = mirror
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        """Open the camera capture device."""
        if self.is_opened():
            return True

        # Use DirectShow backend on Windows for faster initialization and stability
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        self._cap = cv2.VideoCapture(self.device_index, backend)

        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self.device_index)

        if not self._cap.isOpened():
            self.release()
            return False

        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a single frame from the active camera, applying mirror flip for natural selfie orientation."""
        if not self.is_opened():
            return False, None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return False, None

        if self.mirror:
            frame = cv2.flip(frame, 1)

        return True, frame

    def is_opened(self) -> bool:
        """Check if the camera is currently opened."""
        return self._cap is not None and self._cap.isOpened()

    def release(self) -> None:
        """Release the video capture hardware cleanly."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
