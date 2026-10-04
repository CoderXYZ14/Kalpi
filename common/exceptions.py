import logging

from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

from common.responses import error_response

logger = logging.getLogger("api")


def _first_error(errors, path=""):
    if isinstance(errors, dict):
        for key, value in errors.items():
            name = path if key == "non_field_errors" else (f"{path}.{key}" if path else key)
            found = _first_error(value, name)
            if found:
                return found
    elif isinstance(errors, list):
        for value in errors:
            found = _first_error(value, path)
            if found:
                return found
    elif errors:
        return f"{path}: {errors}" if path else str(errors)
    return None


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled error in %s", context["view"].__class__.__name__)
        return error_response("Internal server error", status=500)

    if isinstance(exc, ValidationError):
        return error_response(_first_error(response.data) or "Invalid request", response.status_code, details=response.data)

    message = response.data.get("detail", "Request failed") if isinstance(response.data, dict) else str(response.data)
    return error_response(str(message), response.status_code)
