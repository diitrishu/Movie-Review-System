"""Add image fields to Movie and Person tables

Revision ID: add_image_fields
Revises: previous_revision
Create Date: 2024-03-30 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_image_fields'
down_revision = None  # Update this with your previous migration revision
branch_labels = None
depends_on = None

def upgrade():
    # Add image_path column to Movie table
    op.add_column('movie', sa.Column('image_path', sa.String(255), nullable=True))
    
    # Add image_path column to Person table
    op.add_column('person', sa.Column('image_path', sa.String(255), nullable=True))

def downgrade():
    # Remove image_path column from Movie table
    op.drop_column('movie', 'image_path')
    
    # Remove image_path column from Person table
    op.drop_column('person', 'image_path') 