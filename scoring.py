import math

from CTFd.cache import clear_challenges, clear_standings
from CTFd.models import Awards, Solves, Submissions, Teams, Users, db
from CTFd.utils import get_config
from CTFd.utils.modes import get_model

from .constants import (
    DEFAULT_TARGET_PERCENT,
    INTERNAL_AWARD_CATEGORY,
    INTERNAL_AWARD_NAME,
    MAX_TARGET_PERCENT,
    MIN_TARGET_PERCENT,
    MIN_TARGET_SOLVES,
)
from .models import DynamicScoreSnapshot, DynamicScoreState


def coerce_score_bound(value):
    return int(round(float(value or 0)))


def score_span(challenge):
    return max(
        0,
        coerce_score_bound(challenge.initial) - coerce_score_bound(challenge.minimum),
    )


def clamp_score(challenge, value):
    minimum = coerce_score_bound(challenge.minimum)
    initial = coerce_score_bound(challenge.initial)
    lower = min(minimum, initial)
    upper = max(minimum, initial)
    return max(lower, min(int(round(value)), upper))


def smoothstep(progress):
    progress = max(0.0, min(1.0, progress))
    return progress * progress * (3.0 - (2.0 * progress))


def account_columns():
    model = get_model()
    if model == Teams:
        return model, Submissions.team_id, Solves.team_id
    return model, Submissions.user_id, Solves.user_id


def count_eligible_accounts():
    model = get_model()
    return max(
        1,
        model.query.filter(
            model.hidden == False,  # noqa: E712
            model.banned == False,  # noqa: E712
        ).count(),
    )


def count_active_accounts():
    model, submission_account_column, _ = account_columns()
    active_accounts = (
        db.session.query(db.func.count(db.distinct(submission_account_column)))
        .join(model, submission_account_column == model.id)
        .filter(
            submission_account_column.isnot(None),
            model.hidden == False,  # noqa: E712
            model.banned == False,  # noqa: E712
        )
        .scalar()
    )
    return max(1, int(active_accounts or 0))


def calculate_effective_field(reference_accounts, reference_active_accounts):
    registered = max(1, int(reference_accounts))
    active = max(1, int(reference_active_accounts))
    blended = int(round(math.sqrt(registered * active)))
    return max(active, min(registered, blended))


def calculate_target_percent(challenge):
    raw_decay = float(challenge.decay or 0)
    if raw_decay <= 0:
        return DEFAULT_TARGET_PERCENT
    if raw_decay > 1.0:
        raw_decay = raw_decay / 100.0
    return max(MIN_TARGET_PERCENT, min(raw_decay, MAX_TARGET_PERCENT))


def calculate_target_solves(challenge, effective_field):
    span = score_span(challenge)
    if span <= 0:
        return 1.0

    effective_field = max(1, int(effective_field))
    target_percent = calculate_target_percent(challenge)
    percent_target = int(math.ceil(target_percent * effective_field))
    target_solves = max(min(MIN_TARGET_SOLVES, effective_field), percent_target)
    return float(min(target_solves, effective_field, span))


def raw_curve_value(challenge, target_solves, solves_before):
    if score_span(challenge) <= 0:
        return coerce_score_bound(challenge.minimum)

    function = getattr(challenge, "function", "logarithmic") or "logarithmic"
    if function.lower() == "linear":
        progress = min(max(float(solves_before) / max(target_solves, 1.0), 0.0), 1.0)
        remaining = 1.0 - progress
    else:
        progress = float(solves_before) / max(target_solves, 1.0)
        remaining = 1.0 - smoothstep(progress)

    minimum = float(challenge.minimum)
    span = float(challenge.initial) - minimum
    return minimum + (span * remaining)


def build_score_ladder(challenge, target_solves, solve_count):
    minimum = coerce_score_bound(challenge.minimum)
    initial = coerce_score_bound(challenge.initial)
    if solve_count <= 0:
        return [initial]

    ladder = [initial]
    previous = initial

    for solves_before in range(1, solve_count + 1):
        value = clamp_score(
            challenge, raw_curve_value(challenge, target_solves, solves_before)
        )
        if previous > minimum:
            value = min(value, previous - 1)
        ladder.append(max(minimum, value))
        previous = ladder[-1]

    return ladder


def eligible_solves_query(challenge_id):
    model, _, solve_account_column = account_columns()
    return (
        Solves.query.join(model, solve_account_column == model.id)
        .filter(
            Solves.challenge_id == challenge_id,
            solve_account_column.isnot(None),
            model.hidden == False,  # noqa: E712
            model.banned == False,  # noqa: E712
        )
        .order_by(Solves.id.asc())
    )


def get_or_create_internal_award(solve, challenge, award_value):
    award = Awards(
        user_id=solve.user_id,
        team_id=solve.team_id,
        name=INTERNAL_AWARD_NAME,
        description=f"Preserves the solve-time value for {challenge.name}",
        value=award_value,
        category=INTERNAL_AWARD_CATEGORY,
        date=solve.date,
        requirements={
            "challenge_id": challenge.id,
            "solve_id": solve.id,
            "dynamic_score_internal": True,
        },
    )
    db.session.add(award)
    db.session.flush()
    return award


def get_or_create_score_state(challenge, solve_count):
    state = DynamicScoreState.query.filter_by(challenge_id=challenge.id).first()

    if solve_count <= 0:
        if state is not None:
            db.session.delete(state)
            db.session.flush()
        return None

    if state is None:
        reference_accounts = count_eligible_accounts()
        reference_active_accounts = count_active_accounts()
        effective_field = calculate_effective_field(
            reference_accounts, reference_active_accounts
        )
        state = DynamicScoreState(
            challenge_id=challenge.id,
            reference_accounts=reference_accounts,
            reference_challenges=0,
            reference_active_accounts=reference_active_accounts,
            effective_field=effective_field,
            target_solves=calculate_target_solves(challenge, effective_field),
        )
        db.session.add(state)
        db.session.flush()

    state.effective_field = calculate_effective_field(
        state.reference_accounts, state.reference_active_accounts
    )
    state.target_solves = calculate_target_solves(challenge, state.effective_field)
    return state


def sync_dynamic_awards(challenge, clear_cache=True):
    solves = list(eligible_solves_query(challenge.id).all())
    solve_count = len(solves)
    state = get_or_create_score_state(challenge, solve_count)

    if solve_count <= 0:
        challenge.value = coerce_score_bound(challenge.initial)
        db.session.commit()
        if clear_cache:
            clear_challenges()
            clear_standings()
        return challenge

    ladder = build_score_ladder(challenge, state.target_solves, solve_count)
    current_value = ladder[solve_count]

    existing_snapshots = {
        snapshot.solve_id: snapshot
        for snapshot in DynamicScoreSnapshot.query.filter_by(challenge_id=challenge.id).all()
    }
    active_solve_ids = {solve.id for solve in solves}

    for solve_id, snapshot in list(existing_snapshots.items()):
        if solve_id in active_solve_ids:
            continue
        Awards.query.filter_by(id=snapshot.award_id).delete()
        db.session.delete(snapshot)
        existing_snapshots.pop(solve_id, None)

    for solve_rank, solve in enumerate(solves):
        score_awarded = ladder[solve_rank]
        award_value = score_awarded - current_value
        snapshot = existing_snapshots.get(solve.id)

        if snapshot is None:
            award = get_or_create_internal_award(solve, challenge, award_value)
            snapshot = DynamicScoreSnapshot(
                challenge_id=challenge.id,
                solve_id=solve.id,
                award_id=award.id,
                score_awarded=score_awarded,
            )
            db.session.add(snapshot)
            existing_snapshots[solve.id] = snapshot
            continue

        award = Awards.query.filter_by(id=snapshot.award_id).first()
        if award is None:
            award = get_or_create_internal_award(solve, challenge, award_value)
            snapshot.award_id = award.id

        snapshot.score_awarded = score_awarded
        award.user_id = solve.user_id
        award.team_id = solve.team_id
        award.name = INTERNAL_AWARD_NAME
        award.description = f"Preserves the solve-time value for {challenge.name}"
        award.value = award_value
        award.category = INTERNAL_AWARD_CATEGORY
        award.date = solve.date
        award.requirements = {
            "challenge_id": challenge.id,
            "solve_id": solve.id,
            "dynamic_score_internal": True,
        }

    challenge.value = current_value
    db.session.commit()

    if clear_cache:
        clear_challenges()
        clear_standings()

    return challenge


def cleanup_dynamic_score_state(challenge):
    snapshots = DynamicScoreSnapshot.query.filter_by(challenge_id=challenge.id).all()
    award_ids = [snapshot.award_id for snapshot in snapshots]

    for snapshot in snapshots:
        db.session.delete(snapshot)

    if award_ids:
        Awards.query.filter(Awards.id.in_(award_ids)).delete(synchronize_session=False)

    DynamicScoreState.query.filter_by(challenge_id=challenge.id).delete()


def filter_internal_awards(query, admin=False):
    if admin:
        return query
    return query.filter(Awards.category != INTERNAL_AWARD_CATEGORY)


def patch_award_views():
    def user_awards(self, admin=False):
        import datetime

        awards = Awards.query.filter_by(user_id=self.id).order_by(Awards.date.desc())
        awards = filter_internal_awards(awards, admin=admin)
        freeze = get_config("freeze")
        if freeze and admin is False:
            awards = awards.filter(
                Awards.date < datetime.datetime.utcfromtimestamp(int(freeze))
            )
        return awards.all()

    def team_awards(self, admin=False):
        import datetime

        member_ids = [member.id for member in self.members]
        awards = Awards.query.filter(Awards.user_id.in_(member_ids)).order_by(
            Awards.date.desc()
        )
        awards = filter_internal_awards(awards, admin=admin)
        freeze = get_config("freeze")
        if freeze and admin is False:
            awards = awards.filter(
                Awards.date < datetime.datetime.utcfromtimestamp(int(freeze))
            )
        return awards.all()

    Users.get_awards = user_awards
    Teams.get_awards = team_awards
