"""PUBLIC_MODE=1: user-supplied URLs must not reach the server's own network or filesystem."""

import asyncio

import httpx
import pytest

from app.ingest import policy, repo, safety, site

PUBLIC_IP = "93.184.215.14"


@pytest.fixture
def public(monkeypatch):
    monkeypatch.setenv("PUBLIC_MODE", "1")
    dns = {"acme.test": [PUBLIC_IP], "evil.test": ["10.0.0.7"], "mixed.test": [PUBLIC_IP, "127.0.0.1"]}

    async def resolve(host: str, port: int) -> list[str]:
        if host not in dns:
            raise OSError("no such host")
        return dns[host]

    monkeypatch.setattr(safety, "_resolve", resolve)


def check(url: str) -> None:
    asyncio.run(safety.check_url(url))


@pytest.mark.parametrize("url", [
    "http://localhost:4100/privacy.html", "http://127.0.0.1:8000/health", "http://169.254.169.254/latest/meta-data",
    "http://10.1.2.3/", "http://192.168.0.1/", "http://[::1]/", "http://[::ffff:127.0.0.1]/", "http://0.0.0.0/",
    "http://db.internal/", "file:///etc/passwd", "ftp://acme.test/", "http://evil.test/", "http://mixed.test/",
    "http://nowhere.test/",
])  # fmt: skip
def test_public_mode_rejects_local_and_private_targets(public, url):
    with pytest.raises(safety.UnsafeURL):
        check(url)


def test_public_mode_allows_public_hosts(public):
    check("https://acme.test/privacy")
    check(f"http://{PUBLIC_IP}/privacy")


def test_default_mode_keeps_the_local_demo_working(monkeypatch):
    monkeypatch.delenv("PUBLIC_MODE", raising=False)
    check("http://localhost:4100/privacy.html")
    check("file:///etc/passwd")  # local mode reads local files on purpose (fixture policy, local repos)


def test_public_mode_rejects_local_paths(public, tmp_path):
    (tmp_path / "privacy.html").write_text("<p>policy</p>")
    with pytest.raises(safety.UnsafeURL):
        asyncio.run(policy.fetch(str(tmp_path / "privacy.html")))
    with pytest.raises(safety.UnsafeURL):
        asyncio.run(repo.fetch(str(tmp_path)))


def test_public_mode_blocks_redirect_to_internal_address(public, monkeypatch):
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})

    monkeypatch.setattr(policy, "_transport", httpx.MockTransport(handler))
    with pytest.raises(safety.UnsafeURL):
        asyncio.run(policy.fetch("https://acme.test/privacy"))
    assert requested == ["https://acme.test/privacy"]  # the internal address is never requested


def test_public_mode_site_scan_refuses_before_launching_a_browser(public):
    scan = asyncio.run(site.scan("http://127.0.0.1:4100/public/index.html"))
    assert scan.error and "UnsafeURL" in scan.error and scan.requests == []


def test_oversized_policy_page_is_refused(monkeypatch):
    big = b"<p>" + b"x" * (policy.MAX_BYTES + 1) + b"</p>"
    monkeypatch.setattr(policy, "_transport", httpx.MockTransport(lambda r: httpx.Response(200, content=big)))
    with pytest.raises(ValueError, match="larger than"):
        asyncio.run(policy.fetch("https://acme.test/privacy"))


def test_pdf_policy_gets_a_clear_error(monkeypatch):
    pdf = httpx.Response(200, content=b"%PDF-1.7 ...", headers={"content-type": "application/pdf"})
    monkeypatch.setattr(policy, "_transport", httpx.MockTransport(lambda r: pdf))
    with pytest.raises(ValueError, match="PDF"):
        asyncio.run(policy.fetch("https://acme.test/privacy.pdf"))


def test_russian_policy_in_windows_1251_is_decoded(monkeypatch):
    html = ("<html><body><main><h1>Политика конфиденциальности</h1><p>" + "Мы не передаём ваши данные третьим лицам. " * 5
            + "</p></main></body></html>").encode("cp1251")  # fmt: skip
    resp = httpx.Response(200, content=html, headers={"content-type": "text/html; charset=windows-1251"})
    monkeypatch.setattr(policy, "_transport", httpx.MockTransport(lambda r: resp))
    assert "Мы не передаём ваши данные третьим лицам." in asyncio.run(
        policy.fetch("https://acme.test/privacy")
    )
