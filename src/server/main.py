"""
VerbalForge Question Generation Server

Main entry point for the continuous question generation service.
Orchestrates the generation of GRE questions and stores them in MongoDB.
"""

import argparse
import asyncio
import signal
import sys

from .config import LOG_LEVEL, LOG_FILE, QUESTION_CONFIG
from .config.settings import settings
from .utils import setup_logging
from .services import GeneratorService, MongoDBService
from .models import ServerStats
from .scheduler import TaskScheduler


class VerbalForgeServer:
    """Main server orchestrator"""

    def __init__(self):
        self.logger = None
        self.generator = None
        self.db = None
        self.stats = None
        self.scheduler = None

    def setup(self) -> None:
        """Initialize server components"""
        # Setup logging
        self.logger = setup_logging(LOG_LEVEL, LOG_FILE)
        self.logger.info("Initializing VerbalForge Server")

        # Initialize services
        self.generator = GeneratorService()
        self.generator.initialize()

        self.db = MongoDBService(uri=settings.mongodb_uri, database_name=settings.mongodb_database)
        self.db.connect()

        # Initialize stats and scheduler
        self.stats = ServerStats()
        self.scheduler = TaskScheduler(self.generator, self.db, self.stats)

        # Log configuration
        self._log_configuration()

    def _log_configuration(self) -> None:
        """Log server configuration"""
        tc_cfg = QUESTION_CONFIG["text_completion"]
        se_cfg = QUESTION_CONFIG["sentence_equivalence"]
        rc_cfg = QUESTION_CONFIG["reading_comprehension"]

        tc_total = sum(tc_cfg.values())
        se_total = sum(se_cfg.values())
        rc_passages = rc_cfg["easy"] + rc_cfg["medium"] + rc_cfg["hard"]
        rc_total = rc_passages * rc_cfg["questions_per_passage"]

        self.logger.info("INDEPENDENT WORKER CONFIGURATION:")
        self.logger.info(
            f"  TC Runner: {tc_total} questions per cycle "
            f"({tc_cfg['easy']} easy, {tc_cfg['medium']} medium, {tc_cfg['hard']} hard) "
            f"- Every {self.scheduler.tc_runner.interval_hours}h"
        )
        self.logger.info(
            f"  SE Runner: {se_total} questions per cycle "
            f"({se_cfg['easy']} easy, {se_cfg['medium']} medium, {se_cfg['hard']} hard) "
            f"- Every {self.scheduler.se_runner.interval_hours}h"
        )
        self.logger.info(
            f"  RC Runner: {rc_total} questions per cycle ({rc_passages} passages) "
            f"- Every {self.scheduler.rc_runner.interval_hours}h"
        )
        self.logger.info("")

    async def run(self) -> None:
        """Run the server"""
        try:
            await self.scheduler.run()
        except asyncio.CancelledError:
            self.logger.info("Server task cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Clean shutdown"""
        self.logger.info("Shutting down server")

        if self.scheduler:
            self.scheduler.stop()

        if self.db:
            self.db.disconnect()

        if self.stats:
            self.stats.log_summary(self.logger)

        self.logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='VerbalForge Question Generation Server')
    parser.add_argument(
        '--reset-state',
        action='store_true',
        help='Reset all runner states before starting (clears last run times and schedules)'
    )
    parser.add_argument(
        '--reset-articles',
        action='store_true',
        help='Reset used articles tracking (allows reusing articles)'
    )
    args = parser.parse_args()
    
    # If resetting, do it before initializing server
    if args.reset_state or args.reset_articles:
        # Create temporary DB connection for reset operations
        from .services import MongoDBService
        from .config.settings import settings
        
        temp_db = MongoDBService(settings.mongodb_uri, settings.mongodb_database)
        temp_db.connect()
        
        if args.reset_state:
            print("\n🔄 Resetting runner states...")
            temp_db.reset_runner_states()
            print("✅ Runner states reset successfully\n")
        
        if args.reset_articles:
            print("\n🔄 Resetting used articles tracking...")
            temp_db.reset_used_articles()
            print("✅ Used articles reset successfully\n")
        
        temp_db.disconnect()
    
    # Now initialize and start server
    server = VerbalForgeServer()
    server.setup()

    # Create main task
    main_task = asyncio.create_task(server.run(), name="verbalforge_main")

    # Setup signal handlers
    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, main_task.cancel)
        loop.add_signal_handler(signal.SIGTERM, main_task.cancel)
    except NotImplementedError:
        # Signals not available on some platforms
        pass

    try:
        await main_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Startup failed: {e}")
        sys.exit(1)
