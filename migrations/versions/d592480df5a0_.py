"""empty message

Revision ID: d592480df5a0
Revises: 628de98b3495
Create Date: 2024-06-19 16:11:48.459864

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd592480df5a0'
down_revision = '628de98b3495'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('result', schema=None) as batch_op:
        batch_op.add_column(sa.Column('generated_circuit_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(None, 'generated__circuit', ['generated_circuit_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('result', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('generated_circuit_id')

    # ### end Alembic commands ###
