"""Shared text analysis helpers for the language-oriented graders."""

import re
from typing import Iterable, List, Sequence, Set

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_'-]*")

STOPWORDS: Set[str] = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "for",
    "from",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "me",
    "more",
    "most",
    "my",
    "no",
    "not",
    "of",
    "on",
    "or",
    "our",
    "out",
    "over",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "too",
    "up",
    "us",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
}

FILLER_PHRASES = (
    "it depends",
    "it really depends",
    "there are many ways",
    "there are several ways",
    "hope this helps",
    "as an ai",
    "in today's world",
    "at the end of the day",
    "needless to say",
    "it is important to note",
    "keep in mind that",
    "basically",
    "obviously",
    "simply put",
)

ACTION_MARKERS = (
    "add",
    "avoid",
    "call",
    "check",
    "configure",
    "create",
    "define",
    "ensure",
    "install",
    "pass",
    "remove",
    "replace",
    "return",
    "run",
    "set",
    "start",
    "test",
    "update",
    "use",
    "validate",
    "wrap",
)

SEQUENCE_MARKERS = ("first", "next", "then", "finally", "after that", "step")

CAUSAL_MARKERS = ("because", "since", "due to", "therefore", "as a result", "so that")

PROCESS_MARKERS = ("first", "then", "next", "step", "process", "by ", "using ")

COMPARISON_MARKERS = (
    "whereas",
    "compared",
    "unlike",
    "while",
    "both",
    "difference",
    "versus",
    "vs",
)


def sentences(text: str) -> List[str]:
    """Split text into non-empty sentences."""
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text.strip())
    return [part.strip() for part in parts if part.strip()]


def words(text: str) -> List[str]:
    """Return lowercase word tokens."""
    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]


def content_words(text: str) -> Set[str]:
    """Return unique lowercase words with stopwords removed."""
    return {word for word in words(text) if word not in STOPWORDS and len(word) > 1}


def keyword_coverage(source: str, target: str) -> float:
    """Fraction of source keywords that also appear in the target."""
    source_words = content_words(source)
    if not source_words:
        return 0.0
    return len(source_words & content_words(target)) / len(source_words)


def lexical_similarity(left: str, right: str) -> float:
    """Jaccard similarity over content words."""
    left_words = content_words(left)
    right_words = content_words(right)
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / len(left_words | right_words)


def count_ngram_repetition(text: str, size: int = 3) -> float:
    """Fraction of repeated word n-grams, used as a redundancy signal."""
    tokens = words(text)
    if len(tokens) < size * 2:
        return 0.0
    ngrams = [tuple(tokens[i : i + size]) for i in range(len(tokens) - size + 1)]
    duplicates = len(ngrams) - len(set(ngrams))
    return duplicates / len(ngrams)


def count_phrases(text: str, phrases: Iterable[str]) -> int:
    """Count how many phrases from ``phrases`` occur in the text."""
    lowered = text.lower()
    return sum(1 for phrase in phrases if phrase in lowered)


def count_any(text: str, markers: Iterable[str]) -> int:
    """Count how many markers occur as substrings of the text."""
    lowered = text.lower()
    return sum(1 for marker in markers if marker in lowered)


def has_bullet_structure(text: str) -> bool:
    """Detect markdown bullets or numbered lists."""
    return bool(re.search(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+\S", text))


def has_code_block(text: str) -> bool:
    """Detect fenced markdown code blocks."""
    return "```" in text


def unique_ratio(tokens: Sequence[str]) -> float:
    """Unique-to-total ratio for a token sequence."""
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)
