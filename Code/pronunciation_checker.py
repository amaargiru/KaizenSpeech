"""
pronunciation_checker.py

Offline English Pronunciation Checker Library
Uses Vosk (offline STT) + G2P phoneme comparison

Usage:
    from pronunciation_checker import PronunciationChecker

    checker = PronunciationChecker(model_path="path/to/vosk-model")
    result = checker.check("Hello world")
    print(result.highlighted_phrase)
    print(result.score)
"""

import json
import queue
import sys
from dataclasses import dataclass, field

import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from g2p_en import G2p
from Levenshtein import ratio, opcodes
import nltk

nltk.download('averaged_perceptron_tagger_eng', quiet=True)


# ─── ANSI color codes ───────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"


# ─── Result dataclass ───────────────────────────────────────────

@dataclass
class PronunciationResult:
    """Result of a pronunciation check."""

    score: float
    """Similarity score from 0.0 (completely wrong) to 1.0 (perfect)."""

    expected_text: str
    """The target phrase that should have been spoken."""

    recognized_text: str
    """The phrase actually recognized from speech."""

    expected_phonemes: list[str] = field(default_factory=list)
    """Phoneme list for the expected text."""

    recognized_phonemes: list[str] = field(default_factory=list)
    """Phoneme list for the recognized text."""

    highlighted_phrase: str = ""
    """
    The expected phrase with ANSI color codes:
    green for correct characters, red+bold+underline for errors.
    """

    word_errors: dict = field(default_factory=dict)
    """
    Per-word error details.
    Keys are word indices, values are dicts with:
        - 'word': the expected word
        - 'recognized_as': matched recognized word or None
        - 'error_char_indices': set of character indices with errors
        - 'is_missing': True if the word was not recognized at all
    """

    @property
    def percentage(self) -> int:
        """Score as integer percentage 0-100."""
        return int(self.score * 100)

    @property
    def is_perfect(self) -> bool:
        return self.score >= 0.95

    @property
    def is_good(self) -> bool:
        return self.score >= 0.75

    @property
    def is_fair(self) -> bool:
        return self.score >= 0.50

    @property
    def plain_error_summary(self) -> str:
        """Human-readable error summary without ANSI codes."""
        if self.is_perfect:
            return "Excellent! Near-perfect pronunciation."
        if self.is_good:
            return "Good. Minor issues detected."
        if self.is_fair:
            return "Fair. Some words need practice."
        return "Needs improvement. Try again slowly."


# ─── Main class ──────────────────────────────────────────────────

class PronunciationChecker:
    """
    Offline English pronunciation checker.

    Parameters
    ----------
    model_path : str
        Path to an unzipped Vosk model directory.
    sample_rate : int
        Audio sample rate (Vosk expects 16000).
    block_size : int
        Audio block size for recording.
    silence_timeout : float
        Seconds of silence before recording stops.
    silence_threshold : float
        RMS energy threshold below which audio is considered silence.
    """

    def __init__(
        self,
        model_path: str,
        sample_rate: int = 16000,
        block_size: int = 8000,
        silence_timeout: float = 2.0,
        silence_threshold: float = 200.0,
    ):
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._silence_timeout = silence_timeout
        self._silence_threshold = silence_threshold
        self._audio_queue: queue.Queue = queue.Queue()

        # Enable ANSI colors on Windows
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass

        # Load Vosk model
        try:
            self._model = Model(model_path)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Vosk model from '{model_path}': {e}\n"
                f"Download a model from https://alphacephei.com/vosk/models"
            ) from e

        # Load G2P model
        self._g2p = G2p()

    # ─── Public API ──────────────────────────────────────────

    def check(self, phrase: str, verbose: bool = False) -> PronunciationResult:
        """
        Record speech and check pronunciation against the given phrase.

        Parameters
        ----------
        phrase : str
            The English phrase the user should pronounce.
        verbose : bool
            If True, print intermediate info (phonemes, etc.) to stdout.

        Returns
        -------
        PronunciationResult
            Dataclass with score, phonemes, highlighted phrase, etc.
        """
        if not phrase or not phrase.strip():
            raise ValueError("Phrase must not be empty.")

        phrase = phrase.strip()

        if verbose:
            print(f'📖 Please say: "{phrase}"')
            print("-" * 50)

        # Record and transcribe
        recognized_text = self._record_and_transcribe(verbose=verbose)

        if verbose:
            print(f'✏️  Recognized:  "{recognized_text}"')

        if not recognized_text:
            return PronunciationResult(
                score=0.0,
                expected_text=phrase,
                recognized_text="",
                expected_phonemes=self._text_to_phonemes_flat(phrase),
                recognized_phonemes=[],
                highlighted_phrase=f"{RED}{BOLD}{UNDERLINE}{phrase}{RESET}",
                word_errors={
                    i: {
                        "word": w,
                        "recognized_as": None,
                        "error_char_indices": set(range(len(w))),
                        "is_missing": True,
                    }
                    for i, w in enumerate(phrase.split())
                },
            )

        # Phonemes
        expected_phonemes = self._text_to_phonemes_flat(phrase)
        recognized_phonemes = self._text_to_phonemes_flat(recognized_text)

        if verbose:
            print(f"🔤 Expected phonemes:   {expected_phonemes}")
            print(f"🔤 Recognized phonemes: {recognized_phonemes}")

        # Score
        score = self._compute_score(expected_phonemes, recognized_phonemes)

        # Highlighted phrase and word errors
        highlighted, word_errors = self._build_highlighted_phrase(
            phrase, recognized_text
        )

        return PronunciationResult(
            score=round(score, 3),
            expected_text=phrase,
            recognized_text=recognized_text,
            expected_phonemes=expected_phonemes,
            recognized_phonemes=recognized_phonemes,
            highlighted_phrase=highlighted,
            word_errors=word_errors,
        )

    # ─── Audio recording ─────────────────────────────────────

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}", file=sys.stderr)
        self._audio_queue.put(bytes(indata))

    def _record_and_transcribe(self, verbose: bool = False) -> str:
        recognizer = KaldiRecognizer(self._model, self._sample_rate)
        recognizer.SetWords(True)

        if verbose:
            print("🎤 Listening... (speak now, pause to stop)")

        # Drain any leftover audio from previous calls
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        with sd.RawInputStream(
            samplerate=self._sample_rate,
            blocksize=self._block_size,
            dtype="int16",
            channels=1,
            callback=self._audio_callback,
        ):
            silent_blocks = 0
            max_silent = int(
                self._silence_timeout * self._sample_rate / self._block_size
            )

            while True:
                data = self._audio_queue.get()

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        return text

                audio_data = np.frombuffer(data, dtype=np.int16)
                energy = np.sqrt(
                    np.mean(audio_data.astype(np.float32) ** 2)
                )

                if energy < self._silence_threshold:
                    silent_blocks += 1
                else:
                    silent_blocks = 0

                if silent_blocks > max_silent:
                    final = json.loads(recognizer.FinalResult())
                    return final.get("text", "")

    # ─── Phoneme utilities ───────────────────────────────────

    @staticmethod
    def _strip_stress(phoneme: str) -> str:
        return "".join(c for c in phoneme if not c.isdigit())

    @staticmethod
    def _is_phoneme(token: str) -> bool:
        t = token.strip()
        return bool(t) and t not in (" ", "", ",", ".", "!", "?", "'", "-")

    def _text_to_phonemes_flat(self, text: str) -> list[str]:
        raw = self._g2p(text.lower())
        return [
            self._strip_stress(p.strip())
            for p in raw
            if self._is_phoneme(p)
        ]

    def _word_to_phonemes(self, word: str) -> list[str]:
        raw = self._g2p(word.lower())
        return [
            self._strip_stress(p.strip())
            for p in raw
            if self._is_phoneme(p)
        ]

    def _get_phoneme_letter_mapping(self, word: str) -> list[dict]:
        """
        Map phonemes to character indices within a word.

        Returns list of {'phoneme': str, 'char_indices': list[int]}.
        """
        raw = self._g2p(word.lower())
        phonemes = [
            self._strip_stress(p.strip())
            for p in raw
            if self._is_phoneme(p)
        ]

        if not phonemes:
            return []

        alpha_chars = [(i, c) for i, c in enumerate(word) if c.isalpha()]
        if not alpha_chars:
            return [{"phoneme": p, "char_indices": []} for p in phonemes]

        n_chars = len(alpha_chars)
        n_phon = len(phonemes)

        result = []
        for pi in range(n_phon):
            start = int(round(pi * n_chars / n_phon))
            end = int(round((pi + 1) * n_chars / n_phon))
            end = max(end, start + 1)
            end = min(end, n_chars)
            char_indices = [alpha_chars[j][0] for j in range(start, end)]
            result.append({"phoneme": phonemes[pi], "char_indices": char_indices})

        return result

    # ─── Word alignment (Needleman-Wunsch) ───────────────────

    @staticmethod
    def _align_word_lists(
        expected_words: list[str], recognized_words: list[str]
    ) -> list[tuple]:
        """
        Global alignment of two word lists.
        Returns [(exp_word | None, rec_word | None), ...].
        """
        n = len(expected_words)
        m = len(recognized_words)

        MATCH_SCORE = 2
        MISMATCH_SCORE = -1
        GAP_PENALTY = -2

        def sim(w1, w2):
            if w1.lower() == w2.lower():
                return MATCH_SCORE
            r = ratio(w1.lower(), w2.lower())
            return MATCH_SCORE * r if r > 0.5 else MISMATCH_SCORE

        dp = [[0.0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            dp[i][0] = dp[i - 1][0] + GAP_PENALTY
        for j in range(1, m + 1):
            dp[0][j] = dp[0][j - 1] + GAP_PENALTY

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                match = dp[i - 1][j - 1] + sim(
                    expected_words[i - 1], recognized_words[j - 1]
                )
                delete = dp[i - 1][j] + GAP_PENALTY
                insert = dp[i][j - 1] + GAP_PENALTY
                dp[i][j] = max(match, delete, insert)

        alignment = []
        i, j = n, m
        while i > 0 or j > 0:
            if i > 0 and j > 0:
                s = sim(expected_words[i - 1], recognized_words[j - 1])
                if dp[i][j] == dp[i - 1][j - 1] + s:
                    alignment.append(
                        (expected_words[i - 1], recognized_words[j - 1])
                    )
                    i -= 1
                    j -= 1
                    continue
            if i > 0 and dp[i][j] == dp[i - 1][j] + GAP_PENALTY:
                alignment.append((expected_words[i - 1], None))
                i -= 1
            else:
                alignment.append((None, recognized_words[j - 1]))
                j -= 1

        alignment.reverse()
        return alignment

    # ─── Phoneme-level diff ──────────────────────────────────

    @staticmethod
    def _get_wrong_phoneme_indices(
        expected_phonemes: list[str], recognized_phonemes: list[str]
    ) -> set[int]:
        exp_str = " ".join(expected_phonemes)
        rec_str = " ".join(recognized_phonemes)

        ops = opcodes(exp_str, rec_str)

        wrong_positions = set()
        for op, src_start, src_end, dst_start, dst_end in ops:
            if op in ("replace", "delete"):
                for ci in range(src_start, src_end):
                    wrong_positions.add(ci)

        wrong_indices = set()
        pos = 0
        for pi, phon in enumerate(expected_phonemes):
            phon_start = pos
            phon_end = pos + len(phon)
            if any(ci in wrong_positions for ci in range(phon_start, phon_end)):
                wrong_indices.add(pi)
            pos = phon_end + 1

        return wrong_indices

    # ─── Highlighted phrase builder ──────────────────────────

    def _build_highlighted_phrase(
        self, expected_phrase: str, recognized_text: str
    ) -> tuple[str, dict]:
        """
        Returns (highlighted_string, word_errors_dict).
        """
        expected_words = expected_phrase.split()
        recognized_words = recognized_text.split() if recognized_text else []

        if not recognized_words:
            word_errors = {
                i: {
                    "word": w,
                    "recognized_as": None,
                    "error_char_indices": set(range(len(w))),
                    "is_missing": True,
                }
                for i, w in enumerate(expected_words)
            }
            return (
                f"{RED}{BOLD}{UNDERLINE}{expected_phrase}{RESET}",
                word_errors,
            )

        alignment = self._align_word_lists(expected_words, recognized_words)

        word_error_maps: dict[int, set[int]] = {}
        word_errors: dict[int, dict] = {}
        exp_idx = 0

        for exp_word, rec_word in alignment:
            if exp_word is None:
                continue

            if rec_word is None:
                word_error_maps[exp_idx] = set(range(len(exp_word)))
                word_errors[exp_idx] = {
                    "word": exp_word,
                    "recognized_as": None,
                    "error_char_indices": set(range(len(exp_word))),
                    "is_missing": True,
                }
                exp_idx += 1
                continue

            phon_map = self._get_phoneme_letter_mapping(exp_word)
            exp_phonemes = [pm["phoneme"] for pm in phon_map]
            rec_phonemes = self._word_to_phonemes(rec_word)

            if exp_phonemes == rec_phonemes:
                word_error_maps[exp_idx] = set()
                word_errors[exp_idx] = {
                    "word": exp_word,
                    "recognized_as": rec_word,
                    "error_char_indices": set(),
                    "is_missing": False,
                }
                exp_idx += 1
                continue

            wrong_phon_idx = self._get_wrong_phoneme_indices(
                exp_phonemes, rec_phonemes
            )

            wrong_chars = set()
            for pi in wrong_phon_idx:
                if pi < len(phon_map):
                    wrong_chars.update(phon_map[pi]["char_indices"])

            word_error_maps[exp_idx] = wrong_chars
            word_errors[exp_idx] = {
                "word": exp_word,
                "recognized_as": rec_word,
                "error_char_indices": wrong_chars,
                "is_missing": False,
            }
            exp_idx += 1

        # Build colored string
        parts = []
        for wi, word in enumerate(expected_words):
            if wi > 0:
                parts.append(" ")

            wrong_chars = word_error_maps.get(wi, set(range(len(word))))

            if not wrong_chars:
                parts.append(f"{GREEN}{word}{RESET}")
            elif len(wrong_chars) >= len([c for c in word if c.isalpha()]):
                parts.append(f"{RED}{BOLD}{UNDERLINE}{word}{RESET}")
            else:
                for ci, ch in enumerate(word):
                    if ci in wrong_chars:
                        parts.append(f"{RED}{BOLD}{UNDERLINE}{ch}{RESET}")
                    else:
                        parts.append(f"{GREEN}{ch}{RESET}")

        return "".join(parts), word_errors

    # ─── Score computation ───────────────────────────────────

    @staticmethod
    def _compute_score(
        expected_phonemes: list[str], actual_phonemes: list[str]
    ) -> float:
        expected_str = " ".join(expected_phonemes)
        actual_str = " ".join(actual_phonemes)
        return ratio(expected_str, actual_str)
