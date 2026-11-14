import asyncio

import pytest

from app.sample import build


@pytest.fixture(scope="session")
def fixture_audit():
    """The real pipeline on demo/fixture-app: offline, canned site scan, no LLM."""
    return asyncio.run(build("test"))


@pytest.fixture(scope="session")
def report(fixture_audit):
    return fixture_audit.report
