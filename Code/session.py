import random
from datetime import datetime, timezone
from fsrs import Card, Rating, Scheduler

from diff_highlighter import (
    compute_rating,
    find_closest_variant,
    normalize_for_compare,
    render_diff
)
from storage import save_user_data

def get_fsrs_card(card_state: dict) -> Card:
    try:
        return Card.from_dict(card_state)
    except Exception:
        return Card()

def select_next_card(user_data: dict, now: datetime) -> tuple[dict | None, str | None]:
    """
    Selects next card according to Spec 6.1:
    1. Due cards (due <= now, first_show == False).
    2. 50/50 probabilistic choice between early cards and new cards (first_show == True).
    3. Fallback FIFO by last_shown_at when no due and new cards exhausted.
    """
    cards = list(user_data["cards"].values())
    if not cards:
        return None, None

    due_cards = []
    new_cards = []
    early_cards = []

    for card in cards:
        if card.get("first_show", False):
            new_cards.append(card)
        else:
            fsrs_card = get_fsrs_card(card.get("fsrs_state", {}))
            if fsrs_card.due <= now:
                due_cards.append((card, fsrs_card.due))
            else:
                early_cards.append((card, fsrs_card.due))

    # 1. Due cards priority
    if due_cards:
        due_cards.sort(key=lambda x: x[1])
        return due_cards[0][0], 'due'

    # 2. No due cards: probabilistic or exhaustive
    if new_cards and early_cards:
        if random.random() < 0.5:
            return new_cards[0], 'new'
        else:
            early_cards.sort(key=lambda x: x[1])
            return early_cards[0][0], 'early'

    if new_cards:
        return new_cards[0], 'new'

    if early_cards:
        # Fallback FIFO: prioritize cards shown longest ago
        def last_shown_key(item):
            card, due = item
            last_shown = card.get("last_shown_at")
            return (last_shown or "", due)

        early_cards.sort(key=last_shown_key)
        return early_cards[0][0], 'early'

    return None, None

def handle_first_show(card: dict, config: dict, user_data: dict, logger) -> bool:
    """Handles first show for a new card. Returns False if user exited with /exit."""
    messages = config.get("messages", {})
    thresholds = config.get("rating_thresholds", {})
    easy_max = thresholds.get("easy_max_errors", 1)
    foreign_lang = config.get("languages", {}).get("foreign", "английский")
    user_file = config.get("paths", {}).get("user_data", "user.json")

    prompt_first = messages.get(
        "prompt_first_show",
        "Обучающий показ:\n{native} -> {foreign_first}"
    ).format(native=card["native"], foreign_first=card["foreign_variants"][0])
    print(prompt_first)

    prompt_trans = messages.get(
        "prompt_translation",
        "Переведите на {foreign}: "
    ).format(foreign=foreign_lang)

    try:
        user_input = input(prompt_trans)
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if user_input.strip() == "/exit":
        return False

    user_norm = normalize_for_compare(user_input)
    chosen_ref, chosen_norm, dist = find_closest_variant(user_norm, card["foreign_variants"])
    print(render_diff(chosen_ref, user_norm))
    logger.info("First show attempt: card='%s', input='%s', dist=%d", card["native"], user_input, dist)

    if dist <= easy_max:
        card["first_show"] = False
        save_user_data(user_file, user_data)
        logger.info("First show completed for '%s'.", card["native"])
        return True

    # Muscle memory loop
    while True:
        prompt_repeat = messages.get("prompt_repeat", "Повторите ввод: ")
        try:
            rep_input = input(prompt_repeat)
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        if rep_input.strip() == "/exit":
            return False

        rep_norm = normalize_for_compare(rep_input)
        c_ref, c_norm, r_dist = find_closest_variant(rep_norm, card["foreign_variants"])
        print(render_diff(c_ref, rep_norm))
        logger.info("First show repeat: card='%s', input='%s', dist=%d", card["native"], rep_input, r_dist)

        if r_dist <= easy_max:
            card["first_show"] = False
            save_user_data(user_file, user_data)
            logger.info("First show completed for '%s'.", card["native"])
            return True
def handle_regular_review(card: dict, config: dict, user_data: dict,
                          scheduler: Scheduler, now: datetime, logger) -> bool:
    """Handles regular review of a card. Returns False if user exited with /exit."""
    messages = config.get("messages", {})
    thresholds = config.get("rating_thresholds", {})
    easy_max = thresholds.get("easy_max_errors", 1)
    foreign_lang = config.get("languages", {}).get("foreign", "английский")
    user_file = config.get("paths", {}).get("user_data", "user.json")

    print(card["native"])
    prompt_trans = messages.get(
        "prompt_translation",
        "Переведите на {foreign}: "
    ).format(foreign=foreign_lang)

    try:
        user_input = input(prompt_trans)
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if user_input.strip() == "/exit":
        return False

    user_norm = normalize_for_compare(user_input)
    chosen_ref, chosen_norm, dist = find_closest_variant(user_norm, card["foreign_variants"])
    rating = compute_rating(dist, len(chosen_norm), thresholds)
    print(render_diff(chosen_ref, user_norm))

    # Update FSRS and storage immediately after first input
    fsrs_card = get_fsrs_card(card.get("fsrs_state", {}))
    fsrs_card, review_log = scheduler.review_card(fsrs_card, rating, now)
    card["fsrs_state"] = fsrs_card.to_dict()
    card["last_shown_at"] = now.isoformat()
    card["counters"]["shows"] += 1
    if rating == Rating.Easy:
        card["counters"]["success"] += 1
    else:
        card["counters"]["fail"] += 1

    card["history"].append({
        "timestamp": now.isoformat(),
        "user_input": user_input,
        "chosen_reference": chosen_ref,
        "distance": dist,
        "rating": rating.name
    })
    if len(card["history"]) > 30:
        card["history"].pop(0)

    save_user_data(user_file, user_data)
    logger.info(
        "Review recorded: card='%s', input='%s', dist=%d, rating=%s, next_due=%s",
        card["native"], user_input, dist, rating.name, fsrs_card.due.isoformat()
    )

    # Muscle memory loop if worse than Easy
    if rating != Rating.Easy:
        while True:
            prompt_repeat = messages.get("prompt_repeat", "Повторите ввод: ")
            try:
                rep_input = input(prompt_repeat)
            except (EOFError, KeyboardInterrupt):
                print()
                return False

            if rep_input.strip() == "/exit":
                return False

            rep_norm = normalize_for_compare(rep_input)
            c_ref, c_norm, r_dist = find_closest_variant(rep_norm, card["foreign_variants"])
            print(render_diff(c_ref, rep_norm))
            logger.info("Muscle memory repeat: card='%s', input='%s', dist=%d", card["native"], rep_input, r_dist)

            if r_dist <= easy_max:
                break

    return True

def run_session(config: dict, user_data: dict, logger) -> None:
    fsrs_cfg = config.get("fsrs", {})
    desired_retention = float(fsrs_cfg.get("desired_retention", 0.9))
    max_interval = int(fsrs_cfg.get("maximum_interval", 36500))
    scheduler = Scheduler(desired_retention=desired_retention, maximum_interval=max_interval)

    messages = config.get("messages", {})
    user_name = config.get("user", {}).get("name", "Пользователь")

    notified_no_due = False

    while True:
        now = datetime.now(timezone.utc)
        card, category = select_next_card(user_data, now)
        if card is None:
            print(messages.get("no_phrases", "Нет фраз для изучения."))
            break

        if category != 'due':
            if not notified_no_due:
                print(messages.get("no_due_cards", "Срочных повторений нет, продолжаем обучение."))
                notified_no_due = True
        else:
            notified_no_due = False

        if card.get("first_show", False):
            continue_session = handle_first_show(card, config, user_data, logger)
        else:
            continue_session = handle_regular_review(card, config, user_data, scheduler, now, logger)

        if not continue_session:
            break

    session_end_msg = messages.get(
        "session_end",
        "Сессия завершена. До встречи, {user}!"
    ).format(user=user_name)
    print(session_end_msg)
    logger.info("Learning session ended by user.")
