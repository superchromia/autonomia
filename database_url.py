from pathlib import Path
from urllib.parse import urlparse, urlunparse


CONTAINER_LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "host.docker.internal"}


def normalize_database_url_for_container(url: str) -> str:
    """Ensure DB host resolves to docker service name inside containers."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return url

    in_container = Path("/.dockerenv").exists()
    if not in_container or hostname not in CONTAINER_LOCAL_DB_HOSTS:
        return url

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth += f":{parsed.password}"
        auth += "@"

    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{auth}postgres{port}"

    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
