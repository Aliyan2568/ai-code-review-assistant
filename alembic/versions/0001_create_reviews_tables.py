"""create reviews and review_issues tables

Revision ID: 0001
Revises:
Create Date: 2026-11-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("ai_status", sa.String(length=16), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("total_issues", sa.Integer(), nullable=False),
        sa.Column("high_count", sa.Integer(), nullable=False),
        sa.Column("medium_count", sa.Integer(), nullable=False),
        sa.Column("low_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reviews_created_at", "reviews", ["created_at"])

    op.create_table(
        "review_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("rule", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_review_issues_review_id", "review_issues", ["review_id"])


def downgrade() -> None:
    op.drop_index("ix_review_issues_review_id", table_name="review_issues")
    op.drop_table("review_issues")
    op.drop_index("ix_reviews_created_at", table_name="reviews")
    op.drop_table("reviews")
