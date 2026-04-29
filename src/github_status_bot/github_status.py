"""Fetches and parses Statuspage.io-compatible API endpoints."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

_TIMEOUT = httpx.Timeout(2.0)
_RETRYABLE = {500, 502, 503, 504}


@dataclass(frozen=True)
class Incident:
    id: str
    started_at: datetime | None
    resolved_at: datetime | None


@dataclass(frozen=True)
class Component:
    name: str
    status: str  # operational | degraded_performance | partial_outage | major_outage


@dataclass(frozen=True)
class ServiceStatusResponse:
    indicator: str
    incidents: list[Incident]
    components: list[Component]
    fetch_error: bool


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_status(data: Any) -> str:
    try:
        return str(data["status"]["indicator"])
    except (KeyError, TypeError):
        return "unknown"


def _parse_incidents(data: Any) -> list[Incident]:
    try:
        raw = data["incidents"]
        if not isinstance(raw, list):
            return []
    except (KeyError, TypeError):
        return []

    incidents = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        incidents.append(
            Incident(
                id=str(item.get("id", "")),
                started_at=_parse_dt(item.get("started_at")),
                resolved_at=_parse_dt(item.get("resolved_at")),
            )
        )
    return incidents


def _parse_components(data: Any) -> list[Component]:
    try:
        raw = data["components"]
        if not isinstance(raw, list):
            return []
    except (KeyError, TypeError):
        return []

    components = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        status = str(item.get("status", "operational"))
        if name:
            components.append(Component(name=name, status=status))
    return components


async def _fetch_with_retry(client: httpx.AsyncClient, url: str) -> Any:
    """Fetch url, retrying once on 5xx or timeout. Returns parsed JSON or raises."""
    for attempt in range(2):
        try:
            response = await client.get(url, timeout=_TIMEOUT)
            if response.status_code in _RETRYABLE and attempt == 0:
                continue
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.HTTPStatusError):
            if attempt == 0:
                continue
            raise


async def fetch_service_status(base_url: str) -> ServiceStatusResponse:
    """Concurrently fetch Statuspage.io endpoints for the given base URL."""
    status_url = f"{base_url}/status.json"
    incidents_url = f"{base_url}/incidents/unresolved.json"
    components_url = f"{base_url}/components.json"

    async with httpx.AsyncClient() as client:
        try:
            status_data, incidents_data = await asyncio.gather(
                _fetch_with_retry(client, status_url),
                _fetch_with_retry(client, incidents_url),
            )
        except Exception:
            return ServiceStatusResponse(
                indicator="unknown",
                incidents=[],
                components=[],
                fetch_error=True,
            )

        try:
            components_data = await _fetch_with_retry(client, components_url)
            components = _parse_components(components_data)
        except Exception:
            components = []

    return ServiceStatusResponse(
        indicator=_parse_status(status_data),
        incidents=_parse_incidents(incidents_data),
        components=components,
        fetch_error=False,
    )
