"""
core/logger.py
Centralized logging for Cracka AI.
Logs to console + file with timestamps.
"""

import logging
import os
from datetime import datetime

# Create logs directory
os.makedirs("data/logs", exist_ok=True)

log_file = f"data/logs/cracka_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("CrackaAI")


def log_info(msg: str):
    logger.info(msg)

def log_error(msg: str):
    logger.error(msg)

def log_warn(msg: str):
    logger.warning(msg)

def log_debug(msg: str):
    logger.debug(msg)