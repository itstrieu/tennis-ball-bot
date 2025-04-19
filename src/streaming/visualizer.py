import cv2


class Visualizer:
    """
    Visualizer handles drawing and displaying inference results.
    """

    WINDOW_NAME = "Live Detection"

    @staticmethod
    def show_frame(frame, bboxes):
        """
        Draw bounding boxes and display the frame.

        Args:
            frame (numpy.ndarray): BGR image
            bboxes (list of tuples): each (x, y, w, h)

        Returns:
            bool: False if the user requested exit (pressed 'q'), True otherwise
        """
        for x, y, w, h in bboxes:
            x1, y1 = int(x), int(y)
            x2, y2 = int(x + w), int(y + h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imshow(Visualizer.WINDOW_NAME, frame)
        # exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
            return False
        return True

    @staticmethod
    def cleanup():
        import os

        if os.environ.get("DISPLAY"):
            cv2.destroyWindow(Visualizer.WINDOW_NAME)
