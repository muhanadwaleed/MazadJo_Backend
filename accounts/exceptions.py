from rest_framework.exceptions import APIException


class AccountDisabled(APIException):
    status_code = 403
    default_detail = "This account is disabled."
    default_code = "account_disabled"


class InvalidOtp(APIException):
    status_code = 400
    default_detail = "Invalid or expired code."
    default_code = "invalid_otp"
