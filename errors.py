class AAsheException(Exception):
    """Generic exception for the AAshe library."""
    pass

# 400	Bad request
# 401	Unauthorized
# 403	Forbidden
# 404	Data not found
# 405	Method not allowed
# 415	Unsupported media type
# 429	Rate limit exceeded
# 500	Internal server error
# 502	Bad gateway
# 503	Service unavailable
# 504	Gateway timeout


class BadRequest(AAsheException):
    def __init__(self):
        self.message = "Bad request"
        self.status_code = 400
        

class Unauthorized(AAsheException):
    def __init__(self):
        self.message = "Unauthorized"
        self.status_code = 401
        

class Forbidden(AAsheException):
    def __init__(self):
        self.message = "Forbidden"
        self.status_code = 403


class DataNotFound(AAsheException):
    def __init__(self):
        self.message = "Data not found"
        self.status_code = 404


class MethodNotAllowed(AAsheException):
    def __init__(self):
        self.message = "Method not allowed"
        self.status_code = 405


class UnsupportedMediaType(AAsheException):
    def __init__(self):
        self.message = "Unsupported media type"
        self.status_code = 415


class RateLimitExceeded(AAsheException):
    def __init__(self):
        self.message = "Rate limit exceeded"
        self.status_code = 429


class InternalServerError(AAsheException):
    def __init__(self):
        self.message = "Internal server error"
        self.status_code = 500


class BadGateway(AAsheException):
    def __init__(self):
        self.message = "Bad gateway"
        self.status_code = 502


class ServiceUnavailable(AAsheException):
    def __init__(self):
        self.message = "Service unavailable"
        self.status_code = 503


class GatewayTimeout(AAsheException):
    def __init__(self):
        self.message = "Gateway timeout"
        self.status_code = 504
