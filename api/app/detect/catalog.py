from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel


class Vendor(BaseModel):
    name: str
    packages: list[str] = []
    domains: list[str] = []
    cookies: list[str] = []
    categories: list[str] = []
    purpose: str | None = None
    country: str | None = None
    is_ai: bool = False
    essential: bool = False


@lru_cache
def load_catalog() -> list[Vendor]:
    raw = yaml.safe_load((Path(__file__).parent / "sdk_catalog.yaml").read_text())
    return [Vendor(**v) for v in raw]


@lru_cache
def package_index() -> dict[str, Vendor]:
    return {p.lower(): v for v in load_catalog() for p in v.packages}


def vendor_by_name(name: str | None) -> Vendor | None:
    return next((v for v in load_catalog() if v.name == name), None)
