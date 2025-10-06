GENERATION_INTERVAL_HOURS = 2
QUESTION_CONFIG = {
    "text_completion": {
        "easy": 5,
        "medium": 5,
        "hard": 5,
    },
    "sentence_equivalence": {
        "easy": 5,
        "medium": 5,
        "hard": 5,
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
