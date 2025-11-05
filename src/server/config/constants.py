"""
Configuration Constants

Loads configuration from config.yaml file.
"""

import yaml
from pathlib import Path

# Load configuration from YAML file
config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"

try:
    with open(config_path, 'r') as f:
        _config = yaml.safe_load(f)
except FileNotFoundError:
    raise FileNotFoundError(
        f"Configuration file not found: {config_path}\n"
        "Please create config.yaml in the project root."
    )
except yaml.YAMLError as e:
    raise ValueError(f"Error parsing config.yaml: {e}")

# Extract configuration values
RUNNER_INTERVALS = _config.get('runner_intervals', {
    "tc_runner": 2.0,
    "se_runner": 2.0,
    "rc_runner": 3.0,
})

QUESTION_CONFIG = _config.get('question_config', {
    "text_completion": {"easy": 0, "medium": 2, "hard": 3},
    "sentence_equivalence": {"easy": 0, "medium": 2, "hard": 3},
    "reading_comprehension": {"easy": 0, "medium": 1, "hard": 1, "questions_per_passage": 4},
})

# Logging configuration
_logging_config = _config.get('logging', {})
LOG_LEVEL = _logging_config.get('level', 'INFO')
LOG_FILE = _logging_config.get('file', 'logs/verbalforge.log')

# Timeout settings
_timeouts = _config.get('timeouts', {})
QUESTION_GENERATION_TIMEOUT = _timeouts.get('question_generation', 180)
PASSAGE_GENERATION_TIMEOUT = _timeouts.get('passage_generation', 300)


