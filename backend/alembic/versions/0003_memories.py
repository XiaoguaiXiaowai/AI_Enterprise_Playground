from alembic import op
import sqlalchemy as sa

revision = "0003_memories"
down_revision = "0002_chat_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("namespace", sa.String(length=128), nullable=False, server_default="default"),
        sa.Column("memory_type", sa.String(length=16), nullable=False, server_default="short"),
        sa.Column("key", sa.String(length=128), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memories_user_id", "memories", ["user_id"], unique=False)
    op.create_index("ix_memories_namespace", "memories", ["namespace"], unique=False)
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"], unique=False)
    op.create_index("ix_memories_key", "memories", ["key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_memories_key", table_name="memories")
    op.drop_index("ix_memories_memory_type", table_name="memories")
    op.drop_index("ix_memories_namespace", table_name="memories")
    op.drop_index("ix_memories_user_id", table_name="memories")
    op.drop_table("memories")

