# Manual test for fins control
def test_fins(self):
    """Test the fins manually by activating them with PWM."""
    print("Testing fins...")

    # Turn fins ON with 50% speed
    self.fin_on(speed=100)
    time.sleep(2)  # Keep the fins on for 2 seconds

    # Turn fins OFF
    self.fin_off()
    print("Fins test complete.")

# Call this function when testing the fins
test_fins(self)
