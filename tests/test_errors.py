"""Tests for the error hierarchy."""

from __future__ import annotations

import pytest

from rub.errors import (
    AuthError,
    ExecutionError,
    InvalidArgumentsError,
    OperationNotFoundError,
    ProtocolDetectionError,
    RubError,
    SchemaRetrievalError,
)


class TestRubErrorHierarchy:
    """Verify error hierarchy and attributes."""

    def test_rub_error_is_exception(self):
        assert issubclass(RubError, Exception)

    def test_rub_error_message(self):
        err = RubError("test message")
        assert err.message == "test message"
        assert str(err) == "test message"
        assert err.details is None

    def test_rub_error_details(self):
        err = RubError("msg", details="extra info")
        assert err.details == "extra info"

    @pytest.mark.parametrize(
        "error_cls",
        [
            ProtocolDetectionError,
            SchemaRetrievalError,
            OperationNotFoundError,
            InvalidArgumentsError,
            ExecutionError,
            AuthError,
        ],
    )
    def test_subclass_inherits_rub_error(self, error_cls):
        assert issubclass(error_cls, RubError)
        err = error_cls("test")
        assert isinstance(err, RubError)
        assert isinstance(err, Exception)
        assert err.message == "test"

    def test_can_catch_as_rub_error(self):
        with pytest.raises(RubError):
            raise ProtocolDetectionError("no adapter")

    def test_specific_catch(self):
        with pytest.raises(AuthError):
            raise AuthError("unauthorized", details="token expired")
