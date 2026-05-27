from CTFd.models import db


class DynamicScoreSnapshot(db.Model):
    __tablename__ = "dynamic_score_snapshot"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    solve_id = db.Column(
        db.Integer,
        db.ForeignKey("solves.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    award_id = db.Column(
        db.Integer,
        db.ForeignKey("awards.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    score_awarded = db.Column(db.Integer, nullable=False)


class DynamicScoreState(db.Model):
    __tablename__ = "dynamic_score_state"

    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    reference_accounts = db.Column(db.Integer, nullable=False)
    reference_challenges = db.Column(db.Integer, nullable=False, default=0)
    reference_active_accounts = db.Column(db.Integer, nullable=False)
    effective_field = db.Column(db.Integer, nullable=False)
    target_solves = db.Column(db.Float, nullable=False)
