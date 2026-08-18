"""add ondelete cascade to respiratory_events channel_id fk

Revision ID: cceeb870b81b
Revises: b7b9b5971a41
Create Date: 2026-08-18 14:19:54.976400

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cceeb870b81b'
down_revision: Union[str, None] = 'b7b9b5971a41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Without ON DELETE CASCADE here, deleting a study whose channels have
    # detected respiratory events fails with a ForeignKeyViolation — the
    # ORM's cascade="all, delete-orphan" on Study.channels/.respiratory_events
    # doesn't guarantee respiratory_events are dropped before channels,
    # since channel_id isn't part of that relationship graph. Confirmed via
    # DELETE /studies/{id} on a real uploaded study with detected events.
    op.drop_constraint("respiratory_events_channel_id_fkey", "respiratory_events", type_="foreignkey")
    op.create_foreign_key(
        "respiratory_events_channel_id_fkey",
        "respiratory_events",
        "channels",
        ["channel_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("respiratory_events_channel_id_fkey", "respiratory_events", type_="foreignkey")
    op.create_foreign_key(
        "respiratory_events_channel_id_fkey",
        "respiratory_events",
        "channels",
        ["channel_id"],
        ["id"],
    )
