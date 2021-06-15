"""results table

Revision ID: d2b348622bf7
Revises: 
Create Date: 2020-05-20 08:39:43.585454

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2b348622bf7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('result',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('result', sa.String(length=1200), nullable=True),
    sa.Column('complete', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('result')
    # ### end Alembic commands ###
