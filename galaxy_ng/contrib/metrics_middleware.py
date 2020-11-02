import base64
import json

from django_prometheus.middleware import (
    Metrics,
    PrometheusAfterMiddleware,
    PrometheusBeforeMiddleware,
)

from galaxy_ng.app.auth.auth import RHIdentityAuthentication


EXTENDED_METRICS = [
    "django_http_requests_latency_seconds_by_view_method",
    "django_http_responses_total_by_status_view_method",
    "django_http_requests_total_by_view_transport_method",
]


class AccountEnhancedMetrics(Metrics):
    def register_metric(self, metric_cls, name, documentation, labelnames=(), **kwargs):
        if name in EXTENDED_METRICS:
            labelnames += ("account",)
        return super().register_metric(
            metric_cls, name, documentation, labelnames=labelnames, **kwargs
        )


class AccountEnhancedMetricsBeforeMiddleware(PrometheusBeforeMiddleware):
    metrics_cls = AccountEnhancedMetrics


class AccountEnhancedMetricsAfterMiddleware(PrometheusAfterMiddleware):
    metrics_cls = AccountEnhancedMetrics

    def label_metric(self, metric, request, response=None, **labels):
        new_labels = labels
        if metric._name in EXTENDED_METRICS:
            account = "unknown"
            encoded_identity = request.META.get(RHIdentityAuthentication.header)
            if encoded_identity is not None:
                try:
                    json_string = base64.b64decode(encoded_identity)
                    identity_header = json.loads(json_string)
                    account = identity_header.get("identity", {}).get("account_number", "unknown")
                except ValueError:
                    pass
            new_labels = {"account": account}
            new_labels.update(labels)
        return super().label_metric(metric, request, response=response, **new_labels)
