from alembic import op
import sqlalchemy as sa

revision = "0008_hitl_tables"
down_revision = "0007_agent_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("data_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_target_type", "audit_logs", ["target_type"], unique=False)

    op.create_table(
        "hitl_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("mcp_servers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("arguments_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_status", sa.String(length=16), nullable=True),
        sa.Column("execution_error", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("tool_call_id", sa.Integer(), sa.ForeignKey("mcp_tool_calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hitl_requests_user_id", "hitl_requests", ["user_id"], unique=False)
    op.create_index("ix_hitl_requests_request_id", "hitl_requests", ["request_id"], unique=False)
    op.create_index("ix_hitl_requests_kind", "hitl_requests", ["kind"], unique=False)
    op.create_index("ix_hitl_requests_server_id", "hitl_requests", ["server_id"], unique=False)
    op.create_index("ix_hitl_requests_tool_name", "hitl_requests", ["tool_name"], unique=False)
    op.create_index("ix_hitl_requests_status", "hitl_requests", ["status"], unique=False)
    op.create_index("ix_hitl_requests_decided_by_user_id", "hitl_requests", ["decided_by_user_id"], unique=False)
    op.create_index("ix_hitl_requests_tool_call_id", "hitl_requests", ["tool_call_id"], unique=False)
    op.create_index("ix_hitl_requests_execution_status", "hitl_requests", ["execution_status"], unique=False)

    op.add_column(
        "agent_runs",
        sa.Column("waiting_hitl_request_id", sa.Integer(), nullable=True),
    )
    op.add_column("agent_runs", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_runs", sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agent_runs_waiting_hitl_request_id", "agent_runs", ["waiting_hitl_request_id"], unique=False)

    op.add_column(
        "agent_run_steps",
        sa.Column("hitl_request_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_agent_run_steps_hitl_request_id", "agent_run_steps", ["hitl_request_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_run_steps_hitl_request_id", table_name="agent_run_steps")
    op.drop_column("agent_run_steps", "hitl_request_id")

    op.drop_index("ix_agent_runs_waiting_hitl_request_id", table_name="agent_runs")
    op.drop_column("agent_runs", "resumed_at")
    op.drop_column("agent_runs", "paused_at")
    op.drop_column("agent_runs", "waiting_hitl_request_id")

    op.drop_index("ix_hitl_requests_execution_status", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_tool_call_id", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_decided_by_user_id", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_status", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_tool_name", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_server_id", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_kind", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_request_id", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_user_id", table_name="hitl_requests")
    op.drop_table("hitl_requests")

    op.drop_index("ix_audit_logs_target_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
