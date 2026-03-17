from collections import defaultdict
from threading import Lock
from time import time


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = time()
        self._http_requests_total: dict[tuple[str, str, str], int] = defaultdict(int)
        self._http_errors_total: dict[tuple[str, str], int] = defaultdict(int)
        self._http_request_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._http_request_duration_count: dict[tuple[str, str], int] = defaultdict(int)
        self._http_request_duration_bucket: dict[tuple[str, str], dict[float, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._auth_failures_total: dict[str, int] = defaultdict(int)
        self._auth_rate_limited_total: dict[str, int] = defaultdict(int)
        self._latency_buckets = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def record_http(self, method: str, path: str, status_code: int, duration_seconds: float) -> None:
        status = str(status_code)
        key = (method, path)
        req_key = (method, path, status)
        with self._lock:
            self._http_requests_total[req_key] += 1
            if status_code >= 500:
                self._http_errors_total[key] += 1
            self._http_request_duration_sum[key] += duration_seconds
            self._http_request_duration_count[key] += 1
            for bucket in self._latency_buckets:
                if duration_seconds <= bucket:
                    self._http_request_duration_bucket[key][bucket] += 1

    def record_auth_failure(self, reason: str) -> None:
        with self._lock:
            self._auth_failures_total[reason] += 1

    def record_auth_rate_limited(self, scope: str) -> None:
        with self._lock:
            self._auth_rate_limited_total[scope] += 1

    def render_prometheus(self) -> str:
        with self._lock:
            lines: list[str] = []
            uptime = max(0.0, time() - self._started_at)

            lines.append("# HELP hospital_process_uptime_seconds Process uptime in seconds.")
            lines.append("# TYPE hospital_process_uptime_seconds gauge")
            lines.append(f"hospital_process_uptime_seconds {uptime:.3f}")

            lines.append("# HELP hospital_http_requests_total Total HTTP requests.")
            lines.append("# TYPE hospital_http_requests_total counter")
            for (method, path, status), count in sorted(self._http_requests_total.items()):
                lines.append(
                    f'hospital_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                )

            lines.append("# HELP hospital_http_errors_total Total HTTP 5xx responses.")
            lines.append("# TYPE hospital_http_errors_total counter")
            for (method, path), count in sorted(self._http_errors_total.items()):
                lines.append(f'hospital_http_errors_total{{method="{method}",path="{path}"}} {count}')

            lines.append(
                "# HELP hospital_http_request_duration_seconds HTTP request duration in seconds."
            )
            lines.append("# TYPE hospital_http_request_duration_seconds histogram")
            for key in sorted(self._http_request_duration_count.keys()):
                method, path = key
                cumulative = 0
                for bucket in self._latency_buckets:
                    bucket_count = self._http_request_duration_bucket[key].get(bucket, 0)
                    cumulative += bucket_count
                    lines.append(
                        "hospital_http_request_duration_seconds_bucket"
                        + f'{{method="{method}",path="{path}",le="{bucket}"}} {cumulative}'
                    )
                count = self._http_request_duration_count[key]
                lines.append(
                    "hospital_http_request_duration_seconds_bucket"
                    + f'{{method="{method}",path="{path}",le="+Inf"}} {count}'
                )
                lines.append(
                    f'hospital_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} '
                    + f"{self._http_request_duration_sum[key]:.6f}"
                )
                lines.append(
                    f'hospital_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
                )

            lines.append("# HELP hospital_auth_login_failures_total Total login failures.")
            lines.append("# TYPE hospital_auth_login_failures_total counter")
            for reason, count in sorted(self._auth_failures_total.items()):
                lines.append(f'hospital_auth_login_failures_total{{reason="{reason}"}} {count}')

            lines.append("# HELP hospital_auth_rate_limited_total Total auth rate limit blocks.")
            lines.append("# TYPE hospital_auth_rate_limited_total counter")
            for scope, count in sorted(self._auth_rate_limited_total.items()):
                lines.append(f'hospital_auth_rate_limited_total{{scope="{scope}"}} {count}')

            return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self._lock:
            self._http_requests_total.clear()
            self._http_errors_total.clear()
            self._http_request_duration_sum.clear()
            self._http_request_duration_count.clear()
            self._http_request_duration_bucket.clear()
            self._auth_failures_total.clear()
            self._auth_rate_limited_total.clear()
            self._started_at = time()


metrics_store = MetricsStore()
