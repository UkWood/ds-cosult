"""Safe diagnostics for the DeepSeek transport and its local interpreters."""

import httpx


class ProviderFailure(ValueError):
    def __init__(self, stage, reason, *, exception_class="ValidationError", http_status=None,
                 provider_code=None):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason
        self.exception_class = exception_class
        self.http_status = http_status
        self.provider_code = provider_code

    def diagnostic(self, operation_kind, elapsed_ms, *, response_received=None, http_status=None,
                   financial_outcome_unknown=True):
        status = self.http_status if self.http_status is not None else http_status
        operation = "chat" if operation_kind in {"normal", "extended", "calibration"} else operation_kind
        received = status is not None if response_received is None else response_received
        return dict(operation_kind=operation, failure_stage=self.stage,
                    exception_class=self.exception_class, safe_reason_code=self.reason,
                    http_status=status if type(status) is int and 100 <= status <= 599 else None,
                    provider_error_code=self.provider_code, response_received=received,
                    elapsed_ms=elapsed_ms, financial_outcome_unknown=financial_outcome_unknown)


def transport_failure(error, stage, status):
    for kind, reason in (
        (httpx.ConnectTimeout, "connect_timeout"),
        (httpx.ReadTimeout, "read_timeout"),
        (httpx.WriteTimeout, "write_timeout"),
        (httpx.PoolTimeout, "pool_timeout"),
        (httpx.NetworkError, "network_error"),
        (httpx.ProtocolError, "protocol_error"),
        (httpx.DecodingError, "response_encoding_error"),
    ):
        if isinstance(error, kind):
            return ProviderFailure(stage, reason, exception_class=kind.__name__, http_status=status)
    return ProviderFailure(stage, "transport_error", exception_class="RequestError", http_status=status)
