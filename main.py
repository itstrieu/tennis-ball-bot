import asyncio
import logging
import lgpio

from src.app.demo_robot import DemoRobot
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def main():
    robot = None
    lgpio_handle = None
    log_handlers = setup_logging()
    logger.info("Logging configured.")

    try:
        logger.info("Initializing Robot...")
        robot = DemoRobot()
        await robot.initialize()
        if robot.motion and hasattr(robot.motion, "_gpio_handle"):
            lgpio_handle = robot.motion._gpio_handle
            logger.info(f"Obtained shared lgpio handle: {lgpio_handle}")
        else:
            logger.error("Could not obtain lgpio handle from motion controller.")

        logger.info("Starting Robot run loop...")
        await robot.run()
        logger.info("Robot run loop finished normally.")

    except (KeyboardInterrupt, asyncio.CancelledError) as e:
        logger.warning(
            f"Shutdown signal received ({type(e).__name__}). Initiating cleanup..."
        )

    except Exception as e:
        logger.exception("An unexpected error occurred during robot operation:")

    finally:
        logger.info("--- Main Finally Block: Initiating final cleanup --- ")
        if robot:
            logger.info("Calling robot.cleanup()...")
            try:
                await robot.cleanup()
                logger.info("robot.cleanup() finished.")
            except Exception as e:
                logger.exception("Error during robot.cleanup():")
        else:
            logger.warning("Robot object not initialized, skipping robot.cleanup().")

        if lgpio_handle:
            try:
                logger.info(f"Closing shared lgpio handle {lgpio_handle}...")
                lgpio.gpiochip_close(lgpio_handle)
                logger.info("Shared lgpio handle closed successfully.")
            except lgpio.error as e:
                logger.error(f"Error closing shared lgpio handle {lgpio_handle}: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error closing shared lgpio handle {lgpio_handle}: {e}"
                )
        else:
            logger.warning("No lgpio handle obtained, skipping handle close.")

        logger.info("Cleaning up logging handlers...")
        for handler in log_handlers:
            try:
                handler.close()
                logging.root.removeHandler(handler)
            except Exception as e:
                logger.error(f"Error closing log handler {handler}: {e}")
        logger.info("Cleanup complete. Exiting main.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Critical error during asyncio.run or final shutdown: {e}")
