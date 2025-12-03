import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os

# Define the root path of the project to build an absolute path for the log file
# This makes sure the log file is always created in the correct 'logs' directory
# regardless of where you run the script from.
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOG_FILE_PATH = os.path.join(LOGS_DIR, 'app.log')

def setup_logging():
    """
    Sets up the root logger to output to both console and a rotating file.
    """
    # 1. Define the format for our log messages
    log_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
    )

    # 2. Get the root logger. All other loggers will inherit from this.
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Set the minimum level of logs to capture

    # --- Handlers ---
    # A handler is responsible for dispatching the log message to a destination.
    
    # 3. Create a Console Handler (to see logs in the terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    # 4. Create a Timed Rotating File Handler (for weekly file rotation)
    # This is the core of your requirement.
    file_handler = TimedRotatingFileHandler(
        filename=LOG_FILE_PATH,
        when='W0',  # 'W0' means rotate every Monday (W0=Monday, W1=Tuesday, etc.)
        interval=1, # Rotate every 1 week.
        backupCount=4, # Keep the last 4 log files.
        encoding='utf-8',
        delay=False
    )
    file_handler.setFormatter(log_format)

    # 5. Add the handlers to the root logger
    # Important: Clear any existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.info("Logging configured successfully to console and rotating file.")