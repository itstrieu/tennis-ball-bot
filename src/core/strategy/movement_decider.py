class MovementDecider:
    def __init__(self, target_area, center_threshold, forward_bias=0.7, turn_threshold=50):
        """
        Args:
            target_area (float): area at which object is considered "close enough"
            center_threshold (int): how many pixels off-center counts as "centered"
            forward_bias (float): determines how much more likely the robot is to move forward than rotate
            turn_threshold (int): the distance at which turning becomes important, lower means it prioritizes turning earlier
        """
        self.target_area = target_area
        self.center_threshold = center_threshold
        self.forward_bias = forward_bias  # Prioritize forward motion when ball is in front
        self.turn_threshold = turn_threshold  # Threshold to start turning, adjust as needed

    def decide_direction(self, center_offset):
        """
        Args:
            center_offset (float): pixels from robot's center (positive = right)
        Returns:
            str: "left", "right", or "center"
        """
        if abs(center_offset) > self.turn_threshold:
            if center_offset < 0:
                return "left"
            else:
                return "right"
        else:
            return "center"

    def decide_distance_action(self, area):
        """
        Args:
            area (float): size of detected object
        Returns:
            str: "move" if ball is far, "stop" if close enough
        """
        if area >= self.target_area:
            return "stop"  # Stop when the ball is close enough
        else:
            return "move"  # Move when the ball is far

    def decide(self, offset, area):
        """
        Combines direction + distance into one movement command.
        
        Returns:
            str: "left", "right", "forward", "stop"
        """
        direction = self.decide_direction(offset)
        distance_action = self.decide_distance_action(area)
    
        print(f"[DEBUG] Offset: {offset}, Area: {area}, Direction: {direction}, Distance Action: {distance_action}")
    
        if distance_action == "stop":
            return "stop"
    
        # inside decide_direction:
        if area > 8000 and abs(offset) < 500:
            print("[DEBUG] Close override: pushing forward")
            return "forward"

        if area < 2500 and abs(offset) < 250:
            print("[DEBUG] Far-ball nudge: pushing forward despite offset")
            return "forward"

        # Use dynamic threshold fallback
        dynamic_threshold = min(100, 10 + (area ** 0.5) * 0.8)
        print(f"[DEBUG] Dynamic center threshold: {dynamic_threshold:.2f}")
    
        if abs(offset) <= dynamic_threshold:
            return "forward"
        elif offset < 0:            
	    return "left"
        else:
            return "right"
