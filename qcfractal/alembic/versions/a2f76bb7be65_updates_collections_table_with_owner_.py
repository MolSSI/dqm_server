"""Updates collections table with owner and visibility

Revision ID: a2f76bb7be65
Revises: c194a8ef6acf
Create Date: 2019-10-08 11:06:15.438742

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2f76bb7be65'
down_revision = 'c194a8ef6acf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('collection', sa.Column('description', sa.String(), nullable=True))
    op.add_column('collection', sa.Column('owner', sa.String(length=100), nullable=True))
    op.add_column('collection', sa.Column('view_url', sa.String(length=100), nullable=True))

    op.add_column('collection', sa.Column('view_available', sa.Boolean(), nullable=True))
    op.execute("UPDATE collection SET view_available=false")
    op.alter_column('collection', 'view_available', nullable=False)

    op.add_column('collection', sa.Column('visibility', sa.Boolean(), nullable=True))
    op.execute("UPDATE collection SET visibility=true")
    op.alter_column('collection', 'visibility', nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('collection', 'visibility')
    op.drop_column('collection', 'view_url')
    op.drop_column('collection', 'view_available')
    op.drop_column('collection', 'owner')
    op.drop_column('collection', 'description')
    # ### end Alembic commands ###
