"""Utility functions for AH tests."""


class TaskWaitingTimeout(Exception):
    pass


class CapturingGalaxyError(Exception):
    def __init__(self, http_error, message, http_code=None):
        self.http_error = http_error
        self.message = message
        self.http_code = http_code
