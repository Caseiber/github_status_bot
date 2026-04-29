"""Service registry mapping keyword → Statuspage.io configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ServiceConfig:
    display_name: str
    base_url: str
    status_page_url: str
    ignored_components: frozenset[str] = field(default_factory=frozenset)


SERVICES: dict[str, ServiceConfig] = {
    "github": ServiceConfig(
        display_name="GitHub",
        base_url="https://www.githubstatus.com/api/v2",
        status_page_url="https://www.githubstatus.com",
        ignored_components=frozenset(
            {"Pages", "Webhooks", "Codespaces", "Copilot AI Model Providers"}
        ),
    ),
    "claude": ServiceConfig(
        display_name="Claude",
        base_url="https://status.claude.com/api/v2",
        status_page_url="https://status.claude.com",
    ),
}
