"""
error_handler.py

Centralized error handling and logging utilities.
"""

import logging
import traceback
from typing import Optional, Type, Union, Callable
from functools import wraps
from .logger import Logger

class RobotError(Exception):
    """Base class for robot-specific errors."""
    def __init__(self, message: str, component: str = "unknown"):
        self.message = message
        self.component = component
        super().__init__(f"[{component}] {message}")

def handle_error(
    error_type: Optional[Type[Exception]] = None,
    retry_count: int = 0,
    retry_delay: float = 1.0,
    cleanup: Optional[Callable] = None
):
    """
    Decorator for handling errors in robot components.
    
    Args:
        error_type: Specific exception type to catch (None for all)
        retry_count: Number of times to retry on failure
        retry_delay: Delay between retries in seconds
        cleanup: Cleanup function to call on failure
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if error_type is None or isinstance(e, error_type):
                        last_error = e
                        if attempt < retry_count:
                            Logger.get_logger(func.__module__).warning(
                                f"Attempt {attempt + 1} failed, retrying in {retry_delay}s: {str(e)}"
                            )
                            if cleanup:
                                try:
                                    cleanup()
                                except Exception as cleanup_error:
                                    Logger.get_logger(func.__module__).error(
                                        f"Cleanup failed: {str(cleanup_error)}"
                                    )
                            time.sleep(retry_delay)
                        else:
                            if cleanup:
                                try:
                                    cleanup()
                                except Exception as cleanup_error:
                                    Logger.get_logger(func.__module__).error(
                                        f"Cleanup failed: {str(cleanup_error)}"
                                    )
                            raise RobotError(
                                f"Operation failed after {retry_count + 1} attempts: {str(e)}",
                                component=func.__module__
                            )
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator

class ErrorContext:
    """
    Context manager for error handling.
    Provides cleanup and logging on error.
    """
    def __init__(
        self,
        component: str,
        cleanup: Optional[Callable] = None,
        log_level: int = logging.ERROR
    ):
        self.component = component
        self.cleanup = cleanup
        self.log_level = log_level
        self.logger = Logger.get_logger(component)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.cleanup:
                try:
                    self.cleanup()
                except Exception as e:
                    self.logger.error(f"Cleanup failed: {str(e)}")
                    
            error_msg = f"Error in {self.component}: {str(exc_val)}"
            if exc_tb:
                error_msg += f"\n{traceback.format_tb(exc_tb)}"
                
            self.logger.log(self.log_level, error_msg)
            
            # Don't suppress the exception
            return False

def with_error_handling(
    component: str,
    cleanup: Optional[Callable] = None,
    log_level: int = logging.ERROR
):
    """
    Decorator for error handling with cleanup.
    
    Args:
        component: Name of the component
        cleanup: Cleanup function to call on error
        log_level: Logging level for errors
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with ErrorContext(component, cleanup, log_level):
                return func(*args, **kwargs)
        return wrapper
    return decorator 