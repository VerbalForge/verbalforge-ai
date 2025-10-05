GENERATION_INTERVAL_HOURS = 2
QUESTION_CONFIG = {
    "text_completion": {
        "easy": 0,
        "medium": 5,
        "hard": 5,
    },
    "sentence_equivalence": {
        "easy": 0,
        "medium": 0,
        "hard": 0,
    },
    "reading_comprehension": {
        "easy": 0,
        "medium": 0,
        "hard": 0,
        "questions_per_passage": 0,
    },
}

LOG_LEVEL = "INFO"
LOG_FILE = "logs/verbalforge.log"

QUESTION_GENERATION_TIMEOUT = 180
PASSAGE_GENERATION_TIMEOUT = 300
SHUTDOWN_GRACE_PERIOD = 5
