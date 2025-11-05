"""
Task Scheduler

Orchestrates generation cycles and manages the execution loop.
Runs TC, SE, and RC runners as independent workers with persistent state.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from .services import GeneratorService, MongoDBService
from .models import ServerStats
from .runners import TCRunner, SERunner, RCRunner


class TaskScheduler:
    """Manages independent runner workers"""

    def __init__(self, generator: GeneratorService, db: MongoDBService, stats: ServerStats):
        self.generator = generator
        self.db = db
        self.stats = stats
        self.running = False
        self.logger = logging.getLogger("VerbalForgeServer.Scheduler")
        
        # Initialize runners as independent workers
        self.tc_runner = TCRunner(generator, db)
        self.se_runner = SERunner(generator, db)
        self.rc_runner = RCRunner(generator, db)
        
        # Track worker tasks
        self.worker_tasks: List[asyncio.Task] = []

    def is_running(self) -> bool:
        """Check if scheduler is still running"""
        return self.running

    async def run(self) -> None:
        """Launch all runners as independent workers"""
        self.running = True
        
        try:
            self.logger.info("Starting VerbalForge Scheduler with independent workers")
            self.logger.info(f"TC Runner: every {self.tc_runner.interval_hours}h")
            self.logger.info(f"SE Runner: every {self.se_runner.interval_hours}h")
            self.logger.info(f"RC Runner: every {self.rc_runner.interval_hours}h")
            
            # Launch all runners as independent workers
            self.worker_tasks = [
                asyncio.create_task(self.tc_runner.run_as_worker(), name="TC_Worker"),
                asyncio.create_task(self.se_runner.run_as_worker(), name="SE_Worker"),
                asyncio.create_task(self.rc_runner.run_as_worker(), name="RC_Worker"),
            ]
            
            self.logger.info("All workers launched")
            
            # Wait for all workers to complete (or be cancelled)
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            self.logger.info("Scheduler cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Scheduler error: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Clean shutdown of all workers"""
        self.logger.info("Shutting down scheduler and all workers")
        self.running = False
        
        # Stop all runners
        self.tc_runner.stop()
        self.se_runner.stop()
        self.rc_runner.stop()
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to finish cancelling
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.logger.info("All workers stopped")
        
        # Aggregate stats from all runners
        if self.stats:
            self._aggregate_runner_stats()
            self.stats.log_summary(self.logger)
    
    def _aggregate_runner_stats(self) -> None:
        """Aggregate statistics from all runners into server stats"""
        # Collect stats from all runners
        runners = [self.tc_runner, self.se_runner, self.rc_runner]
        
        total_runs = 0
        successful_runs = 0
        failed_runs = 0
        total_questions = 0
        
        for runner in runners:
            if runner.state:
                total_runs += runner.state.total_runs
                successful_runs += runner.state.successful_runs
                failed_runs += runner.state.failed_runs
                total_questions += runner.state.total_questions_generated
        
        # Update server stats
        self.stats.total_runs = total_runs
        self.stats.successful_runs = successful_runs
        self.stats.failed_runs = failed_runs
        self.stats.total_questions_generated = total_questions
        
        # Log individual runner stats
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("RUNNER STATISTICS")
        self.logger.info("=" * 60)
        
        for runner in runners:
            if runner.state:
                runner_name = runner.runner_id.upper().replace('_', ' ')
                self.logger.info(f"{runner_name}:")
                self.logger.info(f"  Total Runs: {runner.state.total_runs}")
                self.logger.info(f"  Successful: {runner.state.successful_runs}")
                self.logger.info(f"  Failed: {runner.state.failed_runs}")
                self.logger.info(f"  Questions Generated: {runner.state.total_questions_generated}")
                self.logger.info(f"  Next Run: {runner.state.next_run_time}")
                self.logger.info("")
        
        self.logger.info("=" * 60)

    def stop(self) -> None:
        """Stop the scheduler"""
        self.logger.info("Stopping scheduler")
        self.running = False
