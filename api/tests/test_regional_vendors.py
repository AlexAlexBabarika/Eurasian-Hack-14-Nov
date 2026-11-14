"""Vendors common on Kazakhstan and Russian-language products.

Request URLs and cookie names are from live scans of hh.kz, arbuz.kz, naimi.kz, chocolife.me, sulpak.kz and shop.kz.
"""

import re

from app.claims.extract import heuristic
from app.detect import manifests, trackers
from app.detect.catalog import load_catalog
from app.detect.code_signals import CodeSignals
from app.diff.rules import run_rules
from app.ingest.repo import RepoFile
from app.ingest.site import SiteScan
from app.models import Finding, Observation
from app.verdict.engine import finding_status

EN_POLICY = "We collect your email address to create your account."
RU_POLICY = (
    "Политика конфиденциальности\n"
    "Мы собираем адрес электронной почты и сведения об использовании сайта.\n"
    "Для анализа посещаемости мы используем Яндекс.Метрику."
)
METRICA = "https://mc.yandex.ru/metrika/tag.js"
ZERO = "https://c.zero.kz/z.png?u=3735&t=1"


def scan(*requests: str, cookies: tuple[str, ...] = ()) -> list[Observation]:
    found = trackers.detect(SiteScan(url="https://acme.kz", requests=list(requests), cookies=list(cookies)))
    return trackers.merge([], found)


def rules(observations: list[Observation], policy: str = EN_POLICY) -> dict[str, Finding]:
    findings = run_rules(observations, heuristic(policy), CodeSignals(), "https://acme.kz/privacy", 10)
    return {f.rule.split("_")[0]: f for f in findings}


def test_trackers_on_kazakh_sites_are_recognised():
    found = scan(
        METRICA,
        "https://mc.yandex.com/watch/2647417?wmode=7&page-url=https%3A%2F%2Fhh.kz%2F&charset=utf-8",
        "https://yandex.ru/ads/system/context.js",
        "https://yandex.ru/adfox/3726384/getBulk/v2?pr=725357846",
        "https://an.yandex.ru/mapuid/GoogleSspUid/?partner-tag=yandex_ag",
        "https://top-fwz1.mail.ru/js/code.js",
        "https://privacy-cs.mail.ru/static/sync-loader.js",
        "https://vk.com/rtrg?p=VK-RTRG-178026-ax928",
        "https://analytics.tiktok.com/i18n/pixel/events.js?sdkid=C3LVC6VB3D4L4OG4N5JG&lib=ttq",
        "https://websdk.appsflyer.com/?st=banners&",
        ZERO,
        "https://counter.yadro.ru/hit",
        "https://cloud.roistat.com/",
        "https://tracking.retailrocket.ru/",
        "https://api-maps.yandex.ru/2.1/?load=package.standard&lang=ru_RU",
        "https://epay.homebank.kz/payform/payment-api.js",
    )
    assert {o.vendor: (o.purpose_guess, o.vendor_country) for o in found} == {
        "Yandex Metrica": ("analytics", "RU"),
        "Yandex Advertising Network": ("ads", "RU"),
        "VK Ads Pixel": ("ads", "RU"),
        "TikTok Pixel": ("ads", "SG"),
        "AppsFlyer": ("ads", "US"),
        "ZERO.kz": ("analytics", "KZ"),
        "LiveInternet": ("analytics", "RU"),
        "Roistat": ("analytics", "RU"),
        "Retail Rocket": ("personalisation", "RU"),
        "Yandex Maps": ("maps", "RU"),
        "Halyk ePay": ("payments", "KZ"),
    }


def test_other_yandex_and_vk_requests_are_not_trackers():
    assert scan(
        "https://yandex.ru/search/?text=privacy",
        "https://avatars.mds.yandex.net/get-x/1.png",
        "https://vk.com/js/api/openapi.js?159",
    ) == []  # fmt: skip


def test_regional_cookies_are_recognised():
    cookies = ("_ym_uid", "_ym_d", "_ym_isad", "yandexuid", "ymex", "tmr_lvid", "tmr_detect", "_ttp",
               "ttcsid_C3LVC6VB3D4L4OG4N5JG", "_zero_cc", "roistat_visit", "rrpvid", "afUserId", "PHPSESSID",
               "remixlang")  # fmt: skip
    found = scan(cookies=cookies)
    assert {o.vendor for o in found} == {"Yandex Metrica", "VK Ads Pixel", "TikTok Pixel", "ZERO.kz", "Roistat",
                                         "Retail Rocket", "AppsFlyer"}  # fmt: skip
    assert len(next(o for o in found if o.vendor == "Yandex Metrica").evidence) == 5


def test_regional_sdks_in_manifests():
    files = [
        RepoFile(path="web/package.json", text='{"dependencies": {"react-yandex-metrika": "^2", "@2gis/mapgl": "^1", '
                                               '"cloudpayments": "^6", "langchain-gigachat": "^0.1"}}'),
        RepoFile(path="api/requirements.txt", text="yandex-cloud-ml-sdk==0.9.0\nyookassa>=3\n"),
        RepoFile(path="app/pubspec.yaml", text="dependencies:\n  appmetrica_plugin: ^3.0.0\n  mytracker_sdk: ^3.0.0\n"
                                               "  yandex_mapkit: ^4.0.0\n"),
        RepoFile(path="android/app/build.gradle", text="dependencies {\n"
                                                       "    implementation 'com.appsflyer:af-android-sdk:6.15.0'\n}\n"),
    ]  # fmt: skip
    assert {o.vendor for o in manifests.detect(files)} == {
        "Yandex Metrica", "2GIS", "CloudPayments", "GigaChat", "YandexGPT", "YooKassa", "AppMetrica", "myTracker",
        "Yandex Maps", "AppsFlyer",
    }  # fmt: skip


def test_user_content_sent_to_gigachat_needs_an_ai_disclosure():
    files = [
        RepoFile(path="requirements.txt", text="gigachat==0.1.39\n"),
        RepoFile(path="bot/answer.py", text="\n".join([
            "from gigachat import GigaChat",
            "from gigachat.models import Chat, Messages, MessagesRole",
            "def answer(question):",
            "    with GigaChat(credentials=KEY) as giga:",
            "        return giga.chat(Chat(messages=[Messages(role=MessagesRole.USER, content=question)]))",
        ])),
    ]  # fmt: skip
    observed = manifests.detect(files)
    assert observed[0].is_ai and "user_content" in observed[0].data_categories
    r4 = rules(observed, RU_POLICY)["R4"]
    assert "GigaChat" in r4.title
    assert [finding_status(r4, j, "ai_transparency", observed)[0] for j in ("UK", "EU", "KZ")] == ["amber", "red", "red"]
    disclosed = RU_POLICY + "\nОтветы на ваши вопросы формируются с помощью искусственного интеллекта."
    assert "R4" not in rules(observed, disclosed)


def test_russian_policy_naming_yandex_covers_yandex_metrica():
    observed = scan(METRICA, "https://analytics.tiktok.com/i18n/pixel/events.js?sdkid=C3LVC6VB3D4L4OG4N5JG&lib=ttq")
    assert "Яндекс" in heuristic(RU_POLICY).named_processors
    r1 = rules(observed, RU_POLICY)["R1"]
    assert "TikTok Pixel" in r1.title and "Yandex" not in r1.title
    assert "Yandex Metrica" in rules(observed)["R1"].title


def test_analytics_before_consent_differs_by_jurisdiction():
    metrica = scan(METRICA)
    r5 = rules(metrica)["R5"]
    assert [finding_status(r5, j, "personal_data", metrica)[0] for j in ("UK", "EU", "KZ")] == ["amber", "red", "amber"]
    with_ads = scan(METRICA, "https://top-fwz1.mail.ru/js/code.js")
    assert finding_status(rules(with_ads)["R5"], "UK", "personal_data", with_ads)[0] == "red"


def test_maps_and_payment_widgets_are_not_trackers():
    observed = scan("https://api-maps.yandex.ru/2.1/?lang=ru_RU", "https://epay.homebank.kz/payform/payment-api.js")
    assert len(observed) == 2 and "R5" not in rules(observed)


def test_kazakh_vendor_is_not_a_cross_border_transfer_for_kazakhstan():
    home = scan(ZERO)
    r6 = rules(home)["R6"]
    assert finding_status(r6, "KZ", "personal_data", home) is None
    assert finding_status(r6, "EU", "personal_data", home)[0] == "amber"
    abroad = scan(ZERO, METRICA)
    assert finding_status(rules(abroad)["R6"], "KZ", "personal_data", abroad)[0] == "red"


def test_catalog_entries_are_unambiguous():
    catalog = load_catalog()
    names = [v.name for v in catalog]
    assert len(names) == len(set(names))
    packages = [p.lower() for v in catalog for p in v.packages]
    assert sorted(packages) == sorted(set(packages))
    assert all(v.purpose and re.fullmatch(r"[A-Z]{2}", v.country or "") for v in catalog)
