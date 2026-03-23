import sqlalchemy.orm as so


class Base(so.DeclarativeBase):
    __abstract__ = True
