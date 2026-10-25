import functools
from flask import request
from marshmallow import Schema, ValidationError

from app.helpers.response_helper import ResponseHelper


def validate(schema: Schema):
    """
    Decorator factory that validates request data against a Marshmallow schema.

    The deserialized data (types coerced, defaults applied) is passed to the
    route as the `validated` keyword argument, so handlers never re-parse the
    raw form and always see exactly what validation accepted.

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
                form_data = {}
                for key, value in request.form.lists():
                    clean_key = key.rstrip("[]")
                    form_data[clean_key] = value if len(value) > 1 or clean_key == "fields" else value[0]
                data.update(form_data)

            data.update(request.args.to_dict())

            for key, file in request.files.items():
                data[key] = file

            try:
                validated = schema.load(data)
            except ValidationError as e:
                return ResponseHelper.validation_error(e.messages)

            return func(*args, validated=validated, **kwargs)
        return wrapper
    return decorator