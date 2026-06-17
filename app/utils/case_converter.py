import re


def to_camel_case(snake_str: str) -> str:
    """
    Convert snake_case string to camelCase.

    Args:
        snake_str (str): Snake case string.

    Returns:
        str: Camel case string.
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def dict_to_camel_case(data: dict) -> dict:
    """
    Recursively convert all dict keys from snake_case to camelCase.

    Args:
        data (dict): Dictionary with snake_case keys.

    Returns:
        dict: Dictionary with camelCase keys.
    """
    result = {}
    for key, value in data.items():
        camel_key = to_camel_case(key)
        if isinstance(value, dict):
            result[camel_key] = dict_to_camel_case(value)
        elif isinstance(value, list):
            result[camel_key] = [
                dict_to_camel_case(i) if isinstance(i, dict) else i
                for i in value
            ]
        else:
            result[camel_key] = value
    return result