"""Initial migration

Revision ID: 787f2208a33c
Revises:
Create Date: 2026-02-18 02:00:29.854989

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "787f2208a33c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create analyses and triages tables."""
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("detected_format", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("total_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parsed_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parse_success_rate", sa.Float(), nullable=True),
        sa.Column("error_rate", sa.Float(), nullable=True),
        sa.Column("level_counts", sa.JSON(), nullable=True),
        sa.Column("top_errors", sa.JSON(), nullable=True),
        sa.Column("top_sources", sa.JSON(), nullable=True),
        sa.Column("status_codes", sa.JSON(), nullable=True),
        sa.Column("earliest_timestamp", sa.DateTime(), nullable=True),
        sa.Column("latest_timestamp", sa.DateTime(), nullable=True),
        sa.Column("time_span", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyses_filename"), "analyses", ["filename"])
    op.create_index(op.f("ix_analyses_detected_format"), "analyses", ["detected_format"])
    op.create_index(op.f("ix_analyses_created_at"), "analyses", ["created_at"])

    op.create_table(
        "triages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("analysis_id", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("overall_severity", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=True),
        sa.Column("provider_used", sa.String(), nullable=False),
        sa.Column("analysis_time_ms", sa.Float(), nullable=True),
        sa.Column("raw_analysis", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_triages_analysis_id"), "triages", ["analysis_id"])
    op.create_index(op.f("ix_triages_overall_severity"), "triages", ["overall_severity"])
    op.create_index(op.f("ix_triages_created_at"), "triages", ["created_at"])


def downgrade() -> None:
    """Drop triages and analyses tables."""
    op.drop_index(op.f("ix_triages_created_at"), table_name="triages")
    op.drop_index(op.f("ix_triages_overall_severity"), table_name="triages")
    op.drop_index(op.f("ix_triages_analysis_id"), table_name="triages")
    op.drop_table("triages")
    op.drop_index(op.f("ix_analyses_created_at"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_detected_format"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_filename"), table_name="analyses")
    op.drop_table("analyses")
