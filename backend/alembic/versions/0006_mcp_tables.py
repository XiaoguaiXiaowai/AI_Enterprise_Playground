from alembic import op
import sqlalchemy as sa

revision = "0006_mcp_tables"
down_revision = "0005_rag_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("transport", sa.String(length=32), nullable=False),
        sa.Column("server_type", sa.String(length=32), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_mcp_servers_user_name"),
    )
    op.create_index("ix_mcp_servers_user_id", "mcp_servers", ["user_id"], unique=False)
    op.create_index("ix_mcp_servers_name", "mcp_servers", ["name"], unique=False)
    op.create_index("ix_mcp_servers_transport", "mcp_servers", ["transport"], unique=False)
    op.create_index("ix_mcp_servers_server_type", "mcp_servers", ["server_type"], unique=False)

    op.create_table(
        "mcp_tool_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("mcp_servers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ok"),
        sa.Column("input_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("output_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mcp_tool_calls_user_id", "mcp_tool_calls", ["user_id"], unique=False)
    op.create_index("ix_mcp_tool_calls_server_id", "mcp_tool_calls", ["server_id"], unique=False)
    op.create_index("ix_mcp_tool_calls_request_id", "mcp_tool_calls", ["request_id"], unique=False)
    op.create_index("ix_mcp_tool_calls_tool_name", "mcp_tool_calls", ["tool_name"], unique=False)
    op.create_index("ix_mcp_tool_calls_status", "mcp_tool_calls", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mcp_tool_calls_status", table_name="mcp_tool_calls")
    op.drop_index("ix_mcp_tool_calls_tool_name", table_name="mcp_tool_calls")
    op.drop_index("ix_mcp_tool_calls_request_id", table_name="mcp_tool_calls")
    op.drop_index("ix_mcp_tool_calls_server_id", table_name="mcp_tool_calls")
    op.drop_index("ix_mcp_tool_calls_user_id", table_name="mcp_tool_calls")
    op.drop_table("mcp_tool_calls")

    op.drop_index("ix_mcp_servers_server_type", table_name="mcp_servers")
    op.drop_index("ix_mcp_servers_transport", table_name="mcp_servers")
    op.drop_index("ix_mcp_servers_name", table_name="mcp_servers")
    op.drop_index("ix_mcp_servers_user_id", table_name="mcp_servers")
    op.drop_table("mcp_servers")

