from alembic import op
import sqlalchemy as sa

revision = "0004_context_events"
down_revision = "0003_memories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_context_events_request_id", "context_events", ["request_id"], unique=False)
    op.create_index("ix_context_events_user_id", "context_events", ["user_id"], unique=False)
    op.create_index("ix_context_events_event_type", "context_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_context_events_event_type", table_name="context_events")
    op.drop_index("ix_context_events_user_id", table_name="context_events")
    op.drop_index("ix_context_events_request_id", table_name="context_events")
    op.drop_table("context_events")

