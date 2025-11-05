"""
Stateful Worker Base Class

Provides state management and independent worker loop functionality
for all runners.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Callable, Optional

from ..services import MongoDBService
from ..models import RunnerState


class StatefulWorker(ABC):
    """
    Base class for independent workers with persistent state.
    
    Handles:
    - State persistence (load/save to MongoDB)
    - Worker lifecycle (start, run, stop)
    - Scheduled execution based on intervals
    - State updates after each run
    """

    def __init__(
        self,
        db: MongoDBService,
        runner_id: str,
        runner_type: str,
        interval_hours: float,
        logger_name: str
    ):
        self.db = db
        self.runner_id = runner_id
        self.runner_type = runner_type
        self.interval_hours = interval_hours
        self.logger = logging.getLogger(logger_name)
        
        # Worker state
        self.state: Optional[RunnerState] = None
        self.running = False
        
        # Load or initialize state
        self._load_state()

    @abstractmethod
    async def execute_generation(self, running_flag: Callable[[], bool]) -> List[Dict]:
        """
        Execute the actual generation logic.
        Must be implemented by subclasses.
        
        Args:
            running_flag: Callable that returns True while worker should keep running
            
        Returns:
            List of generated questions/items
        """
        pass

    # State Management
    
    def _load_state(self) -> None:
        """Load runner state from database or initialize new state"""
        state_data = self.db.load_runner_state(self.runner_id)
        
        if state_data:
            self.state = RunnerState.from_dict(state_data)
            self.logger.info(
                f"Loaded state: last_run={self.state.last_run_time}, "
                f"next_run={self.state.next_run_time}, "
                f"total_runs={self.state.total_runs}"
            )
        else:
            self._initialize_new_state()
    
    def _initialize_new_state(self) -> None:
        """Initialize new state for first-time run"""
        self.state = RunnerState(
            runner_id=self.runner_id,
            runner_type=self.runner_type,
            interval_hours=self.interval_hours
        )
        self.logger.info(f"Initialized new state for {self.runner_id}")
        self._save_state()
    
    def _save_state(self) -> None:
        """Save runner state to database"""
        if self.state:
            self.db.save_runner_state(self.runner_id, self.state.to_dict())
    
    def _update_state_after_run(self, success: bool, items_generated: int) -> None:
        """
        Update state after a generation run
        
        Args:
            success: Whether the run was successful
            items_generated: Number of items (questions/passages) generated
        """
        if not self.state:
            return
            
        now = datetime.now(timezone.utc)
        self.state.last_run_time = now
        self.state.next_run_time = now + timedelta(hours=self.interval_hours)
        self.state.total_runs += 1
        
        if success:
            self.state.successful_runs += 1
            self.state.total_questions_generated += items_generated
        else:
            self.state.failed_runs += 1
        
        self._save_state()
        
        self.logger.info(
            f"State updated: next_run={self.state.next_run_time}, "
            f"success_rate={self.state.successful_runs}/{self.state.total_runs}"
        )
    
    def should_run_now(self) -> bool:
        """Check if worker should execute now based on schedule"""
        if not self.state or not self.state.next_run_time:
            return True  # No schedule, run immediately
            
        now = datetime.now(timezone.utc)
        return now >= self.state.next_run_time
    
    # Worker Lifecycle
    
    async def run_as_worker(self) -> None:
        """
        Run as an independent worker with persistent state.
        Continuously checks schedule and runs generation when due.
        """
        self.running = True
        self.db.mark_runner_running(self.runner_id, True)
        
        try:
            self._log_worker_start()
            
            # Run immediately if scheduled or first run
            if self.should_run_now():
                self.logger.info("Running initial generation cycle")
                await self._execute_generation_cycle()
            else:
                self.logger.info(f"Next run scheduled for: {self.state.next_run_time}")
            
            # Main worker loop
            await self._worker_loop()
                    
        except asyncio.CancelledError:
            self.logger.info("Worker cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            self._cleanup()
    
    def _log_worker_start(self) -> None:
        """Log worker startup information"""
        self.logger.info(f"Starting worker (interval: {self.interval_hours}h)")
    
    async def _worker_loop(self) -> None:
        """Main worker loop that checks schedule and executes when due"""
        while self.running:
            await self._wait_for_next_run()
            
            # Execute generation if still running and scheduled
            if self.running and self.should_run_now():
                await self._execute_generation_cycle()
    
    async def _wait_for_next_run(self) -> None:
        """Wait until next scheduled run with periodic shutdown checks"""
        now = datetime.now(timezone.utc)
        
        if not self.state or not self.state.next_run_time:
            return
            
        time_until_next = (self.state.next_run_time - now).total_seconds()
        
        if time_until_next <= 0:
            return
        
        # Sleep with periodic checks for shutdown (every minute)
        check_interval = 60
        
        for _ in range(int(time_until_next // check_interval)):
            if not self.running:
                return
            await asyncio.sleep(check_interval)
        
        # Sleep remaining time
        if self.running:
            remaining = time_until_next % check_interval
            if remaining > 0:
                await asyncio.sleep(remaining)
    
    async def _execute_generation_cycle(self) -> None:
        """Execute a single generation cycle and update state"""
        self._log_cycle_start()
        start_time = datetime.now(timezone.utc)
        
        try:
            # Execute generation (implemented by subclass)
            items = await self.execute_generation(lambda: self.running)
            
            # Update state based on results
            success = len(items) > 0
            self._update_state_after_run(success, len(items))
            
            # Log results
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._log_cycle_complete(duration, len(items))
            
        except Exception as e:
            self.logger.error(f"Cycle failed: {e}", exc_info=True)
            self._update_state_after_run(False, 0)
    
    def _log_cycle_start(self) -> None:
        """Log cycle start banner"""
        self.logger.info("=" * 60)
        self.logger.info(f"{self.runner_type.upper()} Generation Cycle Starting")
        self.logger.info("=" * 60)
    
    def _log_cycle_complete(self, duration: float, items_count: int) -> None:
        """Log cycle completion"""
        self.logger.info(
            f"Cycle complete in {duration:.1f}s: {items_count} items generated"
        )
    
    def _cleanup(self) -> None:
        """Cleanup when worker stops"""
        self.running = False
        self.db.mark_runner_running(self.runner_id, False)
        self.logger.info("Worker stopped")
    
    def stop(self) -> None:
        """Stop the worker gracefully"""
        self.logger.info("Stopping worker...")
        self.running = False
