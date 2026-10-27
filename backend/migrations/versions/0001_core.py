"""Milestone A core schema, immutable initial migration."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table("organizations", sa.Column("id", sa.String(64), primary_key=True),
                    sa.Column("name", sa.String(200), nullable=False))
    op.create_table("users", sa.Column("id", sa.String(64), primary_key=True),
                    sa.Column("name", sa.String(200), nullable=False),
                    sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
                    sa.Column("enabled", sa.Boolean(), nullable=False))
    op.create_table("organization_members",
                    sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), primary_key=True),
                    sa.Column("organization_id", sa.String(64), sa.ForeignKey("organizations.id"), primary_key=True),
                    sa.Column("role", sa.String(30), nullable=False))
    op.create_table("assets", sa.Column("id", sa.String(64), primary_key=True),
                    sa.Column("organization_id", sa.String(64), sa.ForeignKey("organizations.id"), nullable=False),
                    sa.Column("name", sa.String(200), nullable=False), sa.Column("kind", sa.String(30), nullable=False))
    op.create_index("ix_assets_organization_id", "assets", ["organization_id"])
    op.create_table("devices", sa.Column("id", sa.String(64), primary_key=True),
                    sa.Column("organization_id", sa.String(64), sa.ForeignKey("organizations.id"), nullable=False),
                    sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
                    sa.Column("enabled", sa.Boolean(), nullable=False),
                    sa.Column("last_seen_at", sa.DateTime(timezone=True)))
    op.create_index("ix_devices_organization_id", "devices", ["organization_id"])
    op.create_table("device_assignments", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id"), nullable=False),
                    sa.Column("asset_id", sa.String(64), sa.ForeignKey("assets.id"), nullable=False),
                    sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("valid_to", sa.DateTime(timezone=True)))
    op.create_index("ix_device_assignments_device_id", "device_assignments", ["device_id"])
    op.create_index("ix_device_assignments_asset_id", "device_assignments", ["asset_id"])
    op.create_table("positions", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("organization_id", sa.String(64), sa.ForeignKey("organizations.id"), nullable=False),
                    sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id"), nullable=False),
                    sa.Column("asset_id", sa.String(64), sa.ForeignKey("assets.id")),
                    sa.Column("sequence_number", sa.BigInteger(), nullable=False),
                    sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("fix_valid", sa.Boolean(), nullable=False),
                    sa.Column("latitude", sa.Float()), sa.Column("longitude", sa.Float()),
                    sa.Column("payload", sa.JSON(), nullable=False), sa.UniqueConstraint("device_id", "sequence_number"))
    op.create_index("ix_positions_asset_time", "positions", ["organization_id", "asset_id", "recorded_at", "id"])
    op.create_table("device_latest",
                    sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id"), primary_key=True),
                    sa.Column("position_id", sa.Integer(), sa.ForeignKey("positions.id"), nullable=False),
                    sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    for table in ["device_latest", "positions", "device_assignments", "devices", "assets",
                  "organization_members", "users", "organizations"]:
        op.drop_table(table)
