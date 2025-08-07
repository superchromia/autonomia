"""fix_chat_config_foreign_key_constraints

Revision ID: b4e332b18255
Revises: 59fe44a021d6
Create Date: 2025-08-07 16:32:09.735132

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b4e332b18255'
down_revision: Union[str, Sequence[str], None] = '59fe44a021d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop existing foreign key constraint if it exists
    try:
        op.drop_constraint(
            "fk_chat_configs_chat_id", 
            "chat_configs", 
            type_="foreignkey"
        )
    except Exception:
        pass  # Constraint might not exist
    
    # Add foreign key constraint with CASCADE delete
    op.create_foreign_key(
        "fk_chat_configs_chat_id", 
        "chat_configs", 
        "chats", 
        ["chat_id"], 
        ["id"], 
        ondelete="CASCADE"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the foreign key constraint
    op.drop_constraint("fk_chat_configs_chat_id", "chat_configs", type_="foreignkey")
    
    # Recreate without CASCADE delete
    op.create_foreign_key(
        "fk_chat_configs_chat_id", 
        "chat_configs", 
        "chats", 
        ["chat_id"], 
        ["id"]
    )
