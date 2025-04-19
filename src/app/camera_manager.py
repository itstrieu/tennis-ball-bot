from picamera2 import Picamera2

_camera = None


def get_camera():
    global _camera
    if _camera is None:
        _camera = Picamera2()
        _camera.configure(
            _camera.create_preview_configuration(
                main={"format": "BGR888", "size": (640, 480)}
            )
        )
        _camera.start()
    return _camera


def stop_camera():
    if _camera is not None:
        _camera.stop()
