"""Find and click a consent banner's reject or accept button: known CMP selectors first, then button text."""

import re
from typing import Literal

Choice = Literal["reject", "accept"]

CLICK_MS = 1500
MAX_LABEL = 40
CMP: dict[Choice, list[str]] = {
    "reject": [
        "#onetrust-reject-all-handler", "#CybotCookiebotDialogBodyButtonDecline", "#didomi-notice-disagree-button",
        "[data-testid=uc-deny-all-button]", ".cky-btn-reject", ".osano-cm-deny", ".cmplz-deny",
    ],
    "accept": [
        "#onetrust-accept-btn-handler", "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
        "#didomi-notice-agree-button", "[data-testid=uc-accept-all-button]", ".cky-btn-accept",
        ".osano-cm-accept-all", ".cmplz-accept",
    ],
}  # fmt: skip
CANDIDATES = ", ".join(f"{s}:visible" for s in ["button", "a", "[role=button]", "input[type=button]", "input[type=submit]"])
LABELS = "els => els.map(e => (e.innerText || e.getAttribute('aria-label') || e.value || '').slice(0, 80))"

_REJECT = re.compile(
    r"^(reject|decline|deny|refuse|disagree|отклонить|отказаться)\b"
    r"|\b(reject|decline|deny|refuse) (all|cookies|optional|additional|non-essential)\b"
    r"|\b(only|just) (the )?(strictly )?(necessary|essential|required)\b"
    r"|\b(necessary|essential|required)( cookies)? only\b"
    r"|^(do not|don't) (accept|allow|consent|agree)\b|^continue without (accepting|consent)"
    r"|только (необходимые|обязательные)"
)
_ACCEPT = re.compile(
    r"^(yes, )?(i )?(accept|agree|allow|consent)\b(?! (selection|selected))|\b(accept|allow) (all|cookies)\b"
    r"|^(got it|ok|okay|yes|ок|хорошо)[!.]?$|^(принять|принимаю|согласен|согласиться|разрешить)\b"
)
_PAYWALL = re.compile(r"\b(subscribe|pay|purchase|buy)\b")  # "reject and subscribe" leaves the page: not a plain refusal


def button_kind(label: str) -> Choice | None:
    """Reject is checked first, so "Accept only necessary" counts as a refusal. Pay-or-consent buttons are skipped."""
    text = " ".join(label.lower().split())
    if not text or len(text) > MAX_LABEL or _PAYWALL.search(text):
        return None
    return "reject" if _REJECT.search(text) else "accept" if _ACCEPT.search(text) else None


def pick(labels: list[str], choice: Choice) -> int | None:
    return next((i for i, label in enumerate(labels) if button_kind(label) == choice), None)


async def click(page, choice: Choice) -> str | None:  # noqa: ANN001 - playwright Page
    """Click the banner button in the page or one of its iframes. Returns its label, or None if there is none."""
    for frame in page.frames:
        try:
            known = frame.locator(", ".join(f"{s}:visible" for s in CMP[choice]))
            if await known.count():
                label = " ".join((await known.first.inner_text(timeout=CLICK_MS)).split())[:MAX_LABEL]
                await known.first.click(timeout=CLICK_MS)
                return label or choice
            buttons = frame.locator(CANDIDATES)
            labels = await buttons.evaluate_all(LABELS)
            if (i := pick(labels, choice)) is not None:
                await buttons.nth(i).click(timeout=CLICK_MS)
                return " ".join(labels[i].split())
        except Exception:  # noqa: BLE001, S112 - a detached or cross-origin frame; try the next one
            continue
    return None
