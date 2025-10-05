"""
Server Statistics Model

Tracks and manages server generation statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ServerStats:
    """Server generation statistics tracker"""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_questions_generated: int = 0
    last_run_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def uptime(self) -> str:
        """Get server uptime as formatted string"""
        uptime_delta = datetime.now(timezone.utc) - self.start_time
        return str(uptime_delta)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100

    def log_summary(self, logger) -> None:
        """Log statistics summary"""
        logger.info("=" * 60)
        logger.info("SERVER STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Uptime: {self.uptime}")
        logger.info(f"Total Runs: {self.total_runs}")
        logger.info(f"Successful: {self.successful_runs}")
        logger.info(f"Failed: {self.failed_runs}")
        logger.info(f"Total Questions: {self.total_questions_generated}")
        logger.info(f"Last Run: {self.last_run_time}")
        logger.info(f"Last Success: {self.last_success_time}")

        if self.total_runs > 0:
            logger.info(f"Success Rate: {self.success_rate:.1f}%")

        logger.info("=" * 60)
