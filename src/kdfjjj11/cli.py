import asyncio
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TransferSpeedColumn,
)

from kdfjjj11.download import (
    BYTES_PER_MIB,
    REQUEST_COUNT,
    DownloadResult,
    measure_download,
)

cli = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=False,
    add_completion=False,
)


async def _download(url: str) -> DownloadResult:
    console = Console(stderr=True)
    with Progress(
        TextColumn("{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(binary_units=True),
        TransferSpeedColumn(),
        console=console,
        transient=True,
        disable=not console.is_terminal,
    ) as progress:
        task_id: TaskID | None = None
        current_request = 0

        def show_progress(
            request_number: int, downloaded: int, total: int | None
        ) -> None:
            nonlocal task_id, current_request
            if request_number != current_request:
                if task_id is not None:
                    progress.remove_task(task_id)
                task_id = progress.add_task(
                    f"Request {request_number}/{REQUEST_COUNT}", total=total
                )
                current_request = request_number
            if task_id is not None:
                progress.update(task_id, completed=downloaded, total=total)

        return await measure_download(url, on_progress=show_progress)


@cli.command()
def download(
    url: Annotated[str, typer.Argument(help="HTTP(S) URL to download.")],
) -> None:
    """Measure download speed over 10 sequential requests."""
    try:
        address = httpx.URL(url)
    except httpx.InvalidURL as exc:
        raise typer.BadParameter("Invalid URL.", param_hint="url") from exc

    if address.scheme not in ("http", "https") or not address.host:
        raise typer.BadParameter(
            "Provide a complete URL starting with http:// or https://.",
            param_hint="url",
        )

    try:
        result = asyncio.run(_download(url))
    except (httpx.HTTPError, httpx.InvalidURL) as exc:
        typer.echo(f"Request failed: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Requests completed: {REQUEST_COUNT}")
    typer.echo(f"Average request time: {result.average_time:.3f} s")
    typer.echo(
        f"Total downloaded: {result.total_size} bytes "
        f"({result.total_size / BYTES_PER_MIB:.3f} MiB)"
    )
    typer.echo(f"Download speed: {result.speed:.3f} MiB/s")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
