#!/usr/bin/env python
"""
Standalone task runner for scheduled monitoring and digests on PythonAnywhere or Cron.
Can be executed via PythonAnywhere 'Tasks' tab:
  /home/<username>/.virtualenvs/worldamaze-env/bin/python /home/<username>/WorldAmaze/run_monitoring_task.py
"""
import sys
import os
import logging

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")

from app.database import init_db
from app.jobs.monitoring_job import run_all_active_watches_monitoring
from app.jobs.digest_job import run_scheduled_digests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worldamaze.task")

if __name__ == "__main__":
    logger.info("Initializing WorldAmaze database if not initialized...")
    init_db()

    logger.info("Executing scheduled monitoring cycle for all active watches...")
    results = run_all_active_watches_monitoring()
    logger.info(f"Monitoring cycle complete. Processed {len(results)} active watches.")

    logger.info("Checking scheduled intelligence digests...")
    run_scheduled_digests()
    logger.info("Scheduled task finished successfully.")
