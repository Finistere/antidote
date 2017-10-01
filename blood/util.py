import re

_first_cap_re = re.compile('(.)([A-Z][a-z]+)')
_all_cap_re = re.compile('([a-z0-9])([A-Z])')


def to_snake_case(s):
    """
    Return a string in snake_case.
    Source: https://stackoverflow.com/a/1176023
    """
    # "getHTTPResponseCode" -> "getHTTP_ResponseCode"
    s = re.sub(_first_cap_re, r'\1_\2', s)
    # "getHTTP_ResponseCode" -> "get_HTTP_Response_Code"
    # -> "get_http_response_code"
    return re.sub(_all_cap_re, r'\1_\2', s).lower()


def to_CamelCase(snake_str):
    return ''.join(s.title() for s in snake_str.split('_'))
