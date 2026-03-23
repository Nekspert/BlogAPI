import sqlalchemy.orm as so


class IdIntPkMixin:
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
