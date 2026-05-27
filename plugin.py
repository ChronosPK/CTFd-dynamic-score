from CTFd.cache import clear_challenges, clear_standings
from CTFd.exceptions.challenges import ChallengeUpdateException
from CTFd.plugins.challenges import BaseChallenge, CHALLENGE_CLASSES
from CTFd.plugins.dynamic_challenges import DynamicChallenge, DynamicValueChallenge
from CTFd.plugins.migrations import upgrade

from .scoring import (
    cleanup_dynamic_score_state,
    patch_award_views,
    sync_dynamic_awards,
)


def calculate_value(cls, challenge):
    return sync_dynamic_awards(challenge)


def update(cls, challenge, request):
    data = request.form or request.get_json()

    for attr, value in data.items():
        if attr in ("initial", "minimum", "decay"):
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ChallengeUpdateException(f"Invalid input for '{attr}'")
        setattr(challenge, attr, value)

    return sync_dynamic_awards(challenge)


def solve(cls, user, team, challenge, request):
    BaseChallenge.solve.__func__(cls, user, team, challenge, request)
    return sync_dynamic_awards(challenge)


def delete(cls, challenge):
    cleanup_dynamic_score_state(challenge)
    BaseChallenge.delete.__func__(cls, challenge)
    clear_challenges()
    clear_standings()


def sync_all_dynamic_challenges():
    for challenge in DynamicChallenge.query.all():
        sync_dynamic_awards(challenge, clear_cache=False)
    clear_challenges()
    clear_standings()


def load(app):
    upgrade(plugin_name="dynamic_score")

    DynamicValueChallenge.calculate_value = classmethod(calculate_value)
    DynamicValueChallenge.update = classmethod(update)
    DynamicValueChallenge.solve = classmethod(solve)
    DynamicValueChallenge.delete = classmethod(delete)
    CHALLENGE_CLASSES["dynamic"] = DynamicValueChallenge

    patch_award_views()
    sync_all_dynamic_challenges()

    print("[dynamic_score] Loaded percentage-based persistent dynamic scoring for CTFd 3.8")
