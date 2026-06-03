import uuid

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


def _error_code(exc, status_code: int) -> str:
    if hasattr(exc, "default_code") and exc.default_code:
        return str(exc.default_code)
    mapping = {
        status.HTTP_400_BAD_REQUEST: "bad_request",
        status.HTTP_401_UNAUTHORIZED: "authentication_failed",
        status.HTTP_403_FORBIDDEN: "permission_denied",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
    }
    return mapping.get(status_code, "error")


def _message_from_details(details) -> str:
    if isinstance(details, dict) and "detail" in details:
        detail = details["detail"]
        if isinstance(detail, list):
            return str(detail[0]) if detail else "Request failed."
        return str(detail)
    if isinstance(details, list) and details:
        return str(details[0])
    return "Request failed."


def mazadjo_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    request = context.get("request")
    request_id = None
    if request is not None:
        request_id = request.headers.get("X-Request-ID") or request.META.get(
            "HTTP_X_REQUEST_ID"
        )
    if not request_id:
        request_id = str(uuid.uuid4())

    details = response.data
    if isinstance(details, dict) and "error" in details:
        return response

    code = _error_code(exc, response.status_code)
    if isinstance(exc, APIException):
        codes = exc.get_codes()
        if isinstance(codes, str):
            code = codes
        elif isinstance(codes, dict):
            for value in codes.values():
                if isinstance(value, str):
                    code = value
                    break
                if isinstance(value, list) and value:
                    code = str(value[0])
                    break

    message = _message_from_details(details)
    if isinstance(details, dict) and set(details.keys()) == {"detail"}:
        details_out = None
    else:
        details_out = details

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": details_out,
            "request_id": request_id,
        }
    }
    return response
