from datetime import datetime

import sqlalchemy as sa
import sqlalchemy.orm as so

from .base import Base
from .mixins.id_int_pk import IdIntPkMixin


class Post(Base, IdIntPkMixin):
    __tablename__ = 'posts'

    title: so.Mapped[str] = so.mapped_column(sa.String(256), nullable=False, index=True)
    content: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)

    created_at: so.Mapped[datetime] = so.mapped_column(
            sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: so.Mapped[datetime] = so.mapped_column(
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now()
    )

    def __repr__(self) -> str:
        return f'<Post(id={self.id}, title={self.title[:20]}...)>'
    