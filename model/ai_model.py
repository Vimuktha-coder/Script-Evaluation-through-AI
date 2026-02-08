# model/ai_model.py
"""
AIScriptEvaluator - lightweight, dependency-light scoring for per-question evaluation.

This implementation:
- Uses difflib.SequenceMatcher for a basic semantic/sequence similarity ratio.
- Uses a simple keyword-overlap measure (words in schema vs answer excluding stopwords).
- Combines both measures into a single score between 0 and 1.
- Produces helpful short feedback indicating missing keywords or main problems.

This is intentionally simple so it runs locally without heavy ML dependencies.
You can replace or extend compare() with an external model or embedding similarity later.
"""

from difflib import SequenceMatcher
import re

# Minimal stopword list (extend if needed)
STOPWORDS = {
    'the','is','in','it','of','and','to','a','an','for','on','that','this','these','those',
    'with','by','be','as','are','or','at','from','which','use','used','using'
}

WORD_RE = re.compile(r'\b[a-zA-Z0-9_+-]+\b')


class AIScriptEvaluator:
    def __init__(self):
        # weights for combining similarity measures
        self.semantic_weight = 0.6
        self.keyword_weight = 0.4

    def _words(self, text):
        if not text:
            return []
        words = WORD_RE.findall(text.lower())
        # remove stopwords
        return [w for w in words if w not in STOPWORDS]

    def _keyword_overlap(self, schema_text, answer_text):
        s_words = set(self._words(schema_text))
        a_words = set(self._words(answer_text))
        if not s_words:
            return 0.0
        common = s_words.intersection(a_words)
        # overlap ratio relative to schema important words
        return len(common) / len(s_words)

    def _semantic_ratio(self, a, b):
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        # SequenceMatcher works best with longer strings; use raw text
        return SequenceMatcher(None, a, b).ratio()

    def compare(self, schema_text, answer_text):
        """
        Returns (score, feedback)
        score : float between 0 and 1
        feedback: short string explaining main issues or positives
        """
        schema_text = (schema_text or "").strip()
        answer_text = (answer_text or "").strip()

        # missing answer
        if not answer_text:
            return 0.0, "Answer missing."

        # compute measures
        sem = self._semantic_ratio(schema_text, answer_text)
        key = self._keyword_overlap(schema_text, answer_text)

        # combined score
        score = (self.semantic_weight * sem) + (self.keyword_weight * key)
        # clamp
        score = max(0.0, min(1.0, score))

        # build feedback
        feedback_parts = []
        # if schema empty -> we cannot judge content, but check answer length
        if not schema_text:
            if len(answer_text.split()) < 5:
                feedback_parts.append("Short answer; no schema to compare.")
            else:
                feedback_parts.append("No schema question provided; saved as extra answer.")
            # minor confidence explanation
            feedback_parts.append(f"Auto-score based on answer length/structure.")
            return score, " ".join(feedback_parts)

        # Check missing keywords
        s_words = set(self._words(schema_text))
        a_words = set(self._words(answer_text))
        missing = s_words - a_words
        # suggest the top few missing words (up to 6)
        if missing:
            missing_list = sorted(missing)[:6]
            feedback_parts.append("Missing key terms: " + ", ".join(missing_list) + ".")

        # semantic guidance
        if sem > 0.85:
            feedback_parts.append("Good semantic match to the expected answer.")
        elif sem > 0.6:
            feedback_parts.append("Partial match — key ideas present but some wording/sequence differs.")
        elif sem > 0.35:
            feedback_parts.append("Low semantic overlap; likely incorrect or incomplete.")
        else:
            feedback_parts.append("Poor match — answer likely incorrect or off-topic.")

        # keyword coverage comment
        if key >= 0.8:
            feedback_parts.append("Most expected keywords present.")
        elif key >= 0.4:
            feedback_parts.append("Some expected keywords present; consider adding missing terms.")
        else:
            feedback_parts.append("Few/no expected keywords present; answer is missing important points.")

        # length check heuristic
        if len(answer_text.split()) < max(3, min(20, len(s_words)//2)):
            feedback_parts.append("Answer is short — consider elaborating.")

        # final feedback
        feedback = " ".join(feedback_parts)
        return score, feedback








