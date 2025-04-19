# src/app/camera_manager.py
from picamera2 import Picamera2

_camera = None  # Shared camera instance


def get_camera():
    """
    This function will initialize and return the shared camera instance.
    The camera will only be initialized once and used by other components.
    """
    global _camera
    if _camera is None:
        _camera = Picamera2()
        _camera.configure(
            _camera.create_video_configuration(
                main={"format": "BGR888", "size": (640, 480)}
            )
        )
        _camera.start()
    return _camera
