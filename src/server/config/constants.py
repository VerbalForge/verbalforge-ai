GENERATION_INTERVAL_HOURS = 2
QUESTION_CONFIG = {
    "text_completion": {
        "easy": 3,
        "medium": 6,
        "hard": 6,
    },
    "sentence_equivalence": {
        "easy": 3,
        "medium": 6,
        "hard": 6,
    },
    "reading_comprehension": {
        "easy": 2,
        "medium": 4,
        "hard": 4,
        "questions_per_passage": 4,
    },
}

LOG_LEVEL = "INFO"
LOG_FILE = "logs/verbalforge.log"

QUESTION_GENERATION_TIMEOUT = 180
PASSAGE_GENERATION_TIMEOUT = 300
SHUTDOWN_GRACE_PERIOD = 5
