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
        """Open the camera capture device with robust multi-index fallback."""
        if self.is_opened():
            return True

        # Try specified device_index first, then indices 0..3
        indices_to_try = [self.device_index] + [i for i in [0, 1, 2, 3] if i != self.device_index]

        for idx in indices_to_try:
            # 1. Try DirectShow on Windows
            if sys.platform.startswith("win"):
                self._cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if self._cap.isOpened():
                    self.device_index = idx
                    self._configure_capture()
                    return True

            # 2. Try Default/MSMF
            self._cap = cv2.VideoCapture(idx)
            if self._cap.isOpened():
                self.device_index = idx
                self._configure_capture()
                return True

        self.release()
        return False

    def _configure_capture(self) -> None:
        """Configure standard frame dimensions and buffer size."""
        if self._cap is not None:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

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
