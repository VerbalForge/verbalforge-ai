"""
Runner State Model

Defines the data structure for runner state persistence.
"""

from datetime import datetime
from typing import Optional, Dict, Any


class RunnerState:
    """Represents the persistent state of a runner"""
    
    def __init__(
        self,
        runner_id: str,
        runner_type: str,
        last_run_time: Optional[datetime] = None,
        next_run_time: Optional[datetime] = None,
        interval_hours: float = 2.0,
        total_runs: int = 0,
        successful_runs: int = 0,
        failed_runs: int = 0,
        total_questions_generated: int = 0,
        is_running: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.runner_id = runner_id
        self.runner_type = runner_type
        self.last_run_time = last_run_time
        self.next_run_time = next_run_time
        self.interval_hours = interval_hours
        self.total_runs = total_runs
        self.successful_runs = successful_runs
        self.failed_runs = failed_runs
        self.total_questions_generated = total_questions_generated
        self.is_running = is_running
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "runner_id": self.runner_id,
            "runner_type": self.runner_type,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "next_run_time": self.next_run_time.isoformat() if self.next_run_time else None,
            "interval_hours": self.interval_hours,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "total_questions_generated": self.total_questions_generated,
            "is_running": self.is_running,
            "metadata": self.metadata,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RunnerState':
        """Create RunnerState from dictionary"""
        from datetime import datetime, timezone
        
        return RunnerState(
            runner_id=data.get("runner_id"),
            runner_type=data.get("runner_type"),
            last_run_time=datetime.fromisoformat(data["last_run_time"]) if data.get("last_run_time") else None,
            next_run_time=datetime.fromisoformat(data["next_run_time"]) if data.get("next_run_time") else None,
            interval_hours=data.get("interval_hours", 2.0),
            total_runs=data.get("total_runs", 0),
            successful_runs=data.get("successful_runs", 0),
            failed_runs=data.get("failed_runs", 0),
            total_questions_generated=data.get("total_questions_generated", 0),
            is_running=data.get("is_running", False),
            metadata=data.get("metadata", {}),
        )
