import string
import unicodedata
import jellyfish
from colorama import Fore
from fsrs import Rating

def is_punct(c: str) -> bool:
    """Checks if character is punctuation (including Unicode punctuation, dashes, quotes)."""
    return unicodedata.category(c).startswith('P') or c in string.punctuation

def normalize_for_compare(text: str) -> str:
    """Normalizes text for comparison: lower, no punct, collapsed spaces, trimmed."""
    text = text.replace('\t', ' ')
    cleaned = ''.join(c for c in text if not is_punct(c))
    return ' '.join(cleaned.lower().split())

def build_ref_norm_mapping(ref_orig: str) -> tuple[str, list[int]]:
    """Returns (ref_norm, map_to_orig) where map_to_orig[j] is index in ref_orig."""
    filtered = []
    for idx, ch in enumerate(ref_orig):
        c = ' ' if ch == '\t' else ch
        if not is_punct(c):
            filtered.append((c, idx))

    norm_chars = []
    map_indices = []
    in_space = True
    for ch, idx in filtered:
        if ch.isspace():
            if not in_space:
                norm_chars.append(' ')
                map_indices.append(idx)
                in_space = True
        else:
            norm_chars.append(ch.lower())
            map_indices.append(idx)
            in_space = False

    while norm_chars and norm_chars[-1] == ' ':
        norm_chars.pop()
        map_indices.pop()

    return ''.join(norm_chars), map_indices

def align_strings(user_norm: str, ref_norm: str) -> tuple[int, list[tuple]]:
    """Levenshtein distance DP alignment returning (dist, operations)."""
    m, n = len(user_norm), len(ref_norm)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if user_norm[i - 1] == ref_norm[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j - 1],  # substitution
                    dp[i - 1][j],      # deletion (extra in user)
                    dp[i][j - 1]       # insertion (missing in user)
                )

    i, j = m, n
    ops = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and user_norm[i - 1] == ref_norm[j - 1]:
            ops.append(('match', user_norm[i - 1], ref_norm[j - 1], j - 1))
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            ops.append(('sub', user_norm[i - 1], ref_norm[j - 1], j - 1))
            i -= 1
            j -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            ops.append(('missing', None, ref_norm[j - 1], j - 1))
            j -= 1
        else:
            ops.append(('extra', user_norm[i - 1], None, j))
            i -= 1

    ops.reverse()
    return dp[m][n], ops

def find_closest_variant(user_norm: str, variants: list[str]) -> tuple[str, str, int]:
    """Finds variant closest by Levenshtein distance. Tie breaker: first in list order."""
    best_variant = variants[0]
    best_norm = normalize_for_compare(variants[0])
    best_dist = jellyfish.levenshtein_distance(user_norm, best_norm)

    for v in variants[1:]:
        v_norm = normalize_for_compare(v)
        dist = jellyfish.levenshtein_distance(user_norm, v_norm)
        if dist < best_dist:
            best_dist = dist
            best_variant = v
            best_norm = v_norm

    return best_variant, best_norm, best_dist

def compute_rating(distance: int, ref_len: int, thresholds: dict) -> Rating:
    """Computes FSRS rating based on Levenshtein distance and thresholds."""
    easy_max = thresholds.get("easy_max_errors", 1)
    if distance <= easy_max:
        return Rating.Easy

    good_pct = thresholds.get("good_max_percent", 20.0)
    hard_pct = thresholds.get("hard_max_percent", 40.0)
    again_min = thresholds.get("again_min_errors", 9)

    good_max = max(easy_max + 1, round(ref_len * (good_pct / 100.0)))
    hard_max = max(good_max + 1, round(ref_len * (hard_pct / 100.0)))

    if hard_max >= again_min:
        hard_max = again_min - 1
    if good_max > hard_max:
        good_max = hard_max

    if distance <= good_max and distance < again_min:
        return Rating.Good
    elif distance <= hard_max and distance < again_min:
        return Rating.Hard
    else:
        return Rating.Again

def render_diff(ref_orig: str, user_norm: str) -> str:
    """Renders diff overlaid onto ref_orig with colorama formatting."""
    ref_norm, map_to_orig = build_ref_norm_mapping(ref_orig)
    dist, ops = align_strings(user_norm, ref_norm)

    extras_before_ref: dict[int, list[str]] = {}
    for op in ops:
        if op[0] == 'extra':
            j = op[3]
            extras_before_ref.setdefault(j, []).append(op[1])

    ref_status: dict[int, str] = {}
    for op in ops:
        if op[0] in ('match', 'sub', 'missing'):
            ref_status[op[3]] = op[0]

    result = []
    last_orig_idx = -1

    for j in range(len(ref_norm)):
        if j in extras_before_ref:
            for extra_ch in extras_before_ref[j]:
                if extra_ch == ' ':
                    result.append(Fore.RED + '_' + Fore.RESET)
                else:
                    result.append(Fore.RED + extra_ch + Fore.RESET)

        orig_idx = map_to_orig[j]
        for p_idx in range(last_orig_idx + 1, orig_idx):
            result.append(Fore.RESET + ref_orig[p_idx])

        last_orig_idx = orig_idx
        orig_ch = ref_orig[orig_idx]
        status = ref_status.get(j, 'match')

        if status == 'match':
            result.append(Fore.GREEN + orig_ch + Fore.RESET)
        elif status == 'sub':
            result.append(Fore.RED + orig_ch + Fore.RESET)
        elif status == 'missing':
            if orig_ch == ' ':
                result.append(Fore.RED + '_' + Fore.RESET)
            else:
                result.append(Fore.RED + orig_ch + Fore.RESET)

    if len(ref_norm) in extras_before_ref:
        for extra_ch in extras_before_ref[len(ref_norm)]:
            if extra_ch == ' ':
                result.append(Fore.RED + '_' + Fore.RESET)
            else:
                result.append(Fore.RED + extra_ch + Fore.RESET)

    for p_idx in range(last_orig_idx + 1, len(ref_orig)):
        result.append(Fore.RESET + ref_orig[p_idx])

    return ''.join(result)
