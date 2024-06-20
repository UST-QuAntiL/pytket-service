"""empty message

Revision ID: 3c7255be0c00
Revises: 6201b3fee644
Create Date: 2024-06-19 14:29:45.725852

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c7255be0c00'
down_revision = '6201b3fee644'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('generated__circuit',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('generated_circuit', sa.String(length=1200), nullable=True),
    sa.Column('input_params', sa.String(length=1200), nullable=True),
    sa.Column('original_depth', sa.Integer(), nullable=True),
    sa.Column('original_width', sa.Integer(), nullable=True),
    sa.Column('original_total_number_of_operations', sa.Integer(), nullable=True),
    sa.Column('original_number_of_multi_qubit_gates', sa.Integer(), nullable=True),
    sa.Column('original_number_of_measurement_operations', sa.Integer(), nullable=True),
    sa.Column('original_number_of_single_qubit_gates', sa.Integer(), nullable=True),
    sa.Column('original_multi_qubit_gate_depth', sa.Integer(), nullable=True),
    sa.Column('complete', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('result', schema=None) as batch_op:
        batch_op.add_column(sa.Column('generated_circuit_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('post_processing_result', sa.String(length=1200), nullable=True))
        batch_op.create_foreign_key(None, 'generated__circuit', ['generated_circuit_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('result', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('post_processing_result')
        batch_op.drop_column('generated_circuit_id')

    op.drop_table('generated__circuit')
    # ### end Alembic commands ###