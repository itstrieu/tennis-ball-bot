"""
error_handler.py

Centralized error handling and logging utilities.
Provides robust error handling for robot components.

This module provides:
- Custom exception types
- Error handling decorators
- Context managers for error handling
- Cleanup and retry mechanisms
"""

import logging
import traceback
from typing import Optional, Type, Union, Callable
from functools import wraps
from .logger import Logger

class RobotError(Exception):
    """
    Base class for robot-specific errors.
    
    This class provides:
    - Component-specific error messages
    - Structured error information
    - Consistent error formatting
    
    Attributes:
        message: Error message
        component: Component where error occurred
    """
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
    
    This decorator provides:
    - Error type filtering
    - Retry mechanism
    - Cleanup on failure
    - Error logging
    
    The error handling process:
    1. Attempts operation
    2. Handles specific error types
    3. Retries if configured
    4. Calls cleanup on failure
    5. Logs errors appropriately
    
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
                            # Log retry attempt
                            Logger.get_logger(func.__module__).warning(
                                f"Attempt {attempt + 1} failed, retrying in {retry_delay}s: {str(e)}"
                            )
                            # Run cleanup if configured
                            if cleanup:
                                try:
                                    cleanup()
                                except Exception as cleanup_error:
                                    Logger.get_logger(func.__module__).error(
                                        f"Cleanup failed: {str(cleanup_error)}"
                                    )
                            time.sleep(retry_delay)
                        else:
                            # Final attempt failed, run cleanup and raise
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
    
    This class provides:
    - Context-based error handling
    - Automatic cleanup on error
    - Error logging
    - Stack trace capture
    
    The error handling process:
    1. Enters context
    2. Executes code
    3. Handles errors if they occur
    4. Runs cleanup
    5. Logs error details
    """
    def __init__(
        self,
        component: str,
        cleanup: Optional[Callable] = None,
        log_level: int = logging.ERROR
    ):
        """
        Initialize error context.
        
        Args:
            component: Name of the component
            cleanup: Cleanup function to call on error
            log_level: Logging level for errors
        """
        self.component = component
        self.cleanup = cleanup
        self.log_level = log_level
        self.logger = Logger.get_logger(component)
        
    def __enter__(self):
        """Enter the error context."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the error context.
        
        This method:
        1. Checks for errors
        2. Runs cleanup if needed
        3. Logs error details
        4. Preserves error propagation
        
        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
            
        Returns:
            bool: False to propagate exceptions
        """
        if exc_type is not None:
            # Run cleanup if configured
            if self.cleanup:
                try:
                    self.cleanup()
                except Exception as e:
                    self.logger.error(f"Cleanup failed: {str(e)}")
                    
            # Format error message with stack trace
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
    
    This decorator provides:
    - Component-specific error handling
    - Cleanup on error
    - Error logging
    - Context management
    
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