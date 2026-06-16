import functools
from flask import request
from marshmallow import Schema, ValidationError

from app.helpers.response_helper import ResponseHelper


def validate(schema: Schema):
    """
    Decorator factory that validates request data against a Marshmallow schema.

    Args:
        schema (Schema): Marshmallow schema instance.

    Returns:
        Callable: Decorated route function.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            data = {}

            if request.is_json:
                data.update(request.get_json(silent=True) or {})
            else:
                data.update(request.form.to_dict())

            data.update(request.args.to_dict())

            for key, file in request.files.items():
                data[key] = file

            try:
                schema.load(data)
            except ValidationError as e:
                return ResponseHelper.validation_error(e.messages)

            return func(*args, **kwargs)
        return wrapper
    return decorator