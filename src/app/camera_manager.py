from picamera2 import Picamera2

_camera = None


def get_camera():
    # Initialize the camera once here
    camera = Picamera2()
    camera.configure(
        camera.create_preview_configuration(
            main={"format": "BGR888", "size": (640, 480)}
        )
    )
    camera.start()
    return camera


def stop_camera():
    if _camera is not None:
        _camera.stop()
