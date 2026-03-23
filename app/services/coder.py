import datetime
import json
from decimal import Decimal
from typing import Any, Callable

import pendulum
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


CONVERTERS: dict[str, Callable[[str], Any]] = {
    'date': lambda x: pendulum.parse(x, exact=True),
    'datetime': lambda x: pendulum.parse(x, exact=True),
    'decimal': Decimal,
}


def object_hook(obj: Any) -> Any:
    _spec_type = obj.get('_spec_type')
    if not _spec_type:
        return obj

    if _spec_type in CONVERTERS:
        return CONVERTERS[_spec_type](obj['val'])
    else:
        raise TypeError(f'Unknown {_spec_type}')


class JsonEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, datetime.datetime):
            return {'val': str(o), '_spec_type': 'datetime'}
        elif isinstance(o, datetime.date):
            return {'val': str(o), '_spec_type': 'date'}
        elif isinstance(o, Decimal):
            return {'val': str(o), '_spec_type': 'decimal'}
        else:
            return jsonable_encoder(o)


class JsonCoder:
    @classmethod
    def encode(cls, value: Any) -> bytes:
        if isinstance(value, JSONResponse):
            return value.body
        return json.dumps(value, cls=JsonEncoder).encode()

    @classmethod
    def decode(cls, value: bytes | str) -> Any:
        if isinstance(value, bytes):
            value = value.decode()
        return json.loads(value, object_hook=object_hook)
