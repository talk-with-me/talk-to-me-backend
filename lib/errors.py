"""
Attribution: https://github.com/avrae/avrae-service/blob/master/lib/errors.py under GPL 3.0

(also, I wrote this code in the first place, and as the original author I give express permission for this project
to use it)

- Andrew Zhu (@mommothazaz123)
"""

from bson.errors import InvalidId
from werkzeug.exceptions import HTTPException

from lib.utils import error


def register_error_handlers(app):
    @app.errorhandler(InvalidId)
    def invalid_id(e):
        return error(400, "invalid ID")

    @app.errorhandler(Error)
    def generic_error(e):
        return error(e.code, e.message)

    # base error handler
    @app.errorhandler(HTTPException)
    def http_exception(e):
        return error(e.code, f"{e.name}: {e.description}")


class Error(Exception):
    """Used to raise a specific error from anywhere, as if return error(...) had been called."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message
