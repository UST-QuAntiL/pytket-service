"""empty message

Revision ID: 79e91529e693
Revises: 978123b2bde5
Create Date: 2024-06-19 16:20:02.906672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '79e91529e693'
down_revision = '978123b2bde5'
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