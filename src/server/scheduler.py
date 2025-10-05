"""
Task Scheduler

Orchestrates generation cycles and manages the execution loop.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .config import GENERATION_INTERVAL_HOURS
from .services import GeneratorService, MongoDBService
from .models import ServerStats
from .tasks import (
    generate_text_completion,
    generate_sentence_equivalence,
    generate_reading_comprehension,
)


class TaskScheduler:
    """Manages scheduled question generation cycles"""

    def __init__(self, generator: GeneratorService, db: MongoDBService, stats: ServerStats):
        self.generator = generator
        self.db = db
        self.stats = stats
        self.running = False
        self.logger = logging.getLogger("VerbalForgeServer.Scheduler")

    def is_running(self) -> bool:
        """Check if scheduler is still running"""
        return self.running

    async def run_generation_cycle(self) -> bool:
        """
        Execute one complete generation cycle

        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Starting generation cycle")
        start_time = datetime.now(timezone.utc)

        try:
            all_questions = []

            # Run each generation task
            if self.running:
                tc_questions = await generate_text_completion(
                    self.generator, self.db, self.is_running
                )
                all_questions.extend(tc_questions)

            if self.running:
                se_questions = await generate_sentence_equivalence(
                    self.generator, self.db, self.is_running
                )
                all_questions.extend(se_questions)

            if self.running:
                rc_questions = await generate_reading_comprehension(
                    self.generator, self.db, self.is_running
                )
                all_questions.extend(rc_questions)

            if not self.running:
                self.logger.info("Cycle interrupted by shutdown")
                return False

            # Update stats
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            self.stats.total_runs += 1
            self.stats.last_run_time = end_time

            if all_questions:
                self.stats.successful_runs += 1
                self.stats.last_success_time = end_time
                self.stats.total_questions_generated += len(all_questions)

                self.logger.info(
                    f"Cycle completed in {duration:.1f}s - "
                    f"{len(all_questions)} questions generated"
                )
                return True
            else:
                self.stats.failed_runs += 1
                self.logger.error("No questions generated")
                return False

        except Exception as e:
            self.stats.failed_runs += 1
            self.logger.error(f"Cycle failed: {e}")
            return False

    async def run(self) -> None:
        """Main scheduler loop"""
        self.running = True

        try:
            # Run initial cycle
            self.logger.info("Running initial generation cycle")
            await self.run_generation_cycle()
            self.stats.log_summary(self.logger)

            # Main loop
            while self.running:
                next_run = datetime.now(timezone.utc) + timedelta(hours=GENERATION_INTERVAL_HOURS)
                self.logger.info(f"Next cycle scheduled for: {next_run}")

                # Sleep with periodic shutdown checks
                sleep_total = GENERATION_INTERVAL_HOURS * 3600
                check_interval = 5  # Check every 5 seconds

                for _ in range(int(sleep_total // check_interval)):
                    if not self.running:
                        break
                    await asyncio.sleep(check_interval)

                # Sleep remaining time
                if self.running:
                    remaining = sleep_total % check_interval
                    await asyncio.sleep(remaining)

                # Run next cycle
                if self.running:
                    await self.run_generation_cycle()
                    self.stats.log_summary(self.logger)

        except asyncio.CancelledError:
            self.logger.info("Scheduler cancelled")
            raise

    def stop(self) -> None:
        """Stop the scheduler"""
        self.logger.info("Stopping scheduler")
        self.running = False
