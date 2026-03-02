"""Add chat_sessions table

Revision ID: 003_add_chat_sessions
Revises: 002_analytics_events
Create Date: 2026-03-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_add_chat_sessions"
down_revision: Union[str, None] = "002_analytics_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "chat_sessions" in table_names:
        return

    op.create_table(
        "chat_sessions",
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("planning_stage", sa.String(), nullable=False, server_default="discover"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(op.f("ix_chat_sessions_session_id"), "chat_sessions", ["session_id"], unique=False)
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_chat_sessions_planning_stage"), "chat_sessions", ["planning_stage"], unique=False)
    op.create_index(op.f("ix_chat_sessions_expires_at"), "chat_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_chat_sessions_created_at"), "chat_sessions", ["created_at"], unique=False)
    op.create_index(op.f("ix_chat_sessions_updated_at"), "chat_sessions", ["updated_at"], unique=False)
    op.create_index(
        "idx_chat_sessions_user_stage",
        "chat_sessions",
        ["user_id", "planning_stage"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "chat_sessions" not in table_names:
        return

    op.drop_index("idx_chat_sessions_user_stage", table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_updated_at"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_created_at"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_expires_at"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_planning_stage"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_session_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")
