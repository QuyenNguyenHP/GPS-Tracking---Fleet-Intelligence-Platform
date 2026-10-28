"""Account login, expiring sessions and platform administration."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"


def upgrade():
    op.add_column("organizations", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("username", sa.String(100), nullable=True))
        batch.add_column(sa.Column("password_hash", sa.String(300), nullable=True))
        batch.add_column(sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_unique_constraint("uq_users_username", ["username"])
    op.create_table("login_sessions",
                    sa.Column("token_hash", sa.String(64), primary_key=True),
                    sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_login_sessions_user_id", "login_sessions", ["user_id"])
    op.create_index("ix_login_sessions_expires_at", "login_sessions", ["expires_at"])


def downgrade():
    op.drop_table("login_sessions")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_username", type_="unique")
        batch.drop_column("is_platform_admin")
        batch.drop_column("password_hash")
        batch.drop_column("username")
    op.drop_column("organizations", "enabled")
