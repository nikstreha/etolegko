from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

import httpx

REQUEST_COUNT = 10
BYTES_PER_MIB = 1024**2


@dataclass(frozen=True, slots=True, kw_only=True)
class DownloadResult:
    total_time: float
    total_size: int

    @property
    def average_time(self) -> float:
        return self.total_time / REQUEST_COUNT

    @property
    def speed(self) -> float:
        if self.total_time == 0:
            return 0.0
        return self.total_size / self.total_time / BYTES_PER_MIB


async def measure_download(
    url: str,
    on_progress: Callable[[int, int, int | None], None] | None = None,
) -> DownloadResult:
    total_time = 0.0
    total_size = 0

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        for request_number in range(1, REQUEST_COUNT + 1):
            downloaded = 0
            if on_progress is not None:
                on_progress(request_number, downloaded, None)

            started_at = perf_counter()
            last_reported_at = started_at

            async with client.stream("GET", url) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length", "")
                expected_size = (
                    int(content_length) if content_length.isdecimal() else None
                )
                if on_progress is not None:
                    on_progress(request_number, downloaded, expected_size)

                async for chunk in response.aiter_raw():
                    total_size += len(chunk)
                    downloaded += len(chunk)
                    now = perf_counter()
                    if on_progress is not None and now - last_reported_at >= 0.1:
                        on_progress(request_number, downloaded, expected_size)
                        last_reported_at = now

            total_time += perf_counter() - started_at
            if on_progress is not None:
                on_progress(request_number, downloaded, downloaded)

    return DownloadResult(total_time=total_time, total_size=total_size)
