from asyncio.log import logger
from typing import Optional


def normalize_difficulty(difficulty: Optional[str]) -> str:
    """
    Normalize difficulty level to lowercase standard format.

    Args:
        difficulty: Difficulty level string (e.g., "Easy", "MEDIUM", "Hard")

    Returns:
        Normalized difficulty level: "easy", "medium", or "hard"
        Defaults to "medium" if None or unrecognized
    """
    if not difficulty:
        return "medium"

    normalized = difficulty.lower().strip()
    if normalized in ("easy", "medium", "hard"):
        return normalized

    return "medium"


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    # Remove leading ```json or ``` and trailing ``` if present
    if t.startswith("```"):
        # Remove first fence line
        first_newline = t.find("\n")
        if first_newline != -1:
            t = t[first_newline + 1:]
        # Remove trailing fence if present
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
    return t


def extract_json_payload(text: str) -> str:
    """
    Attempt to extract the first valid JSON array/object from text.
    """
    # Check if response content is empty or None
    if not text or text.strip() == "":
        logger.error("LLM returned empty response content")
        raise Exception("LLM returned empty response")

    s = _strip_code_fences(text)
    # Fast path: already starts with [ or {
    if s[:1] in ("[", "{"):
        return s
    # Fallback: find first [ or { and last matching ] or }
    start_idx = min([i for i in [s.find("{"), s.find("[")] if i != -1], default=-1)
    if start_idx == -1:
        return s
    # Try bracket matching for both object and array
    candidates = []
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        i = s.find(open_ch, start_idx)
        if i == -1:
            continue
        depth = 0
        for j, ch in enumerate(s[i:], start=i):
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    candidates.append(s[i:j + 1])
                    break
    return candidates[0] if candidates else s
