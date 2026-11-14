"""Keyword heuristics for Russian and Kazakh policies. Most Kazakhstan products publish their policy in Russian."""

import re

from app.models import PolicyClaims

_CYRILLIC = re.compile(r"[а-яёәғқңөұүһі]", re.I)
_LETTER = re.compile(r"[^\W\d_]")

_CATEGORIES = {
    "email": r"электронн\w* почт|e-?mail|электрондық пошта",
    "name": r"\bФИО\b|фамили[яюиейё]|отчеств|(?:ваше|своё|свое) имя|аты-жөн",
    "phone": r"телефон",
    "usage": r"аналитик|статистическ|сведени\w* об использовании|как вы используете|посещени\w* (?:сайт|страниц)"
    r"|пайдалану туралы",
    "device_id": r"устройств|идентификатор|құрылғы|сәйкестендіргіш",
    "ip": r"\bIP[- ]?(?:адрес|мекенжай)",
    "user_content": r"(?:ваш\w*|размещаем\w*|загружаем\w*) (?:сообщени|запрос|контент|материал|фотографи|файл|объявлени)"
    r"|контент, который вы|(?:сіздің|пайдаланушының) (?:хабарлама|сұрау|контент|файл)",
    "payment": r"плат[её]ж|оплат|банковск\w* карт|төлем|банк картас",
    "location": r"местоположени|местонахождени|геолокац|геоданн|орналасқан жер",
    "health": r"здоровь|денсаулы",
}

_NO_SHARE = re.compile(
    r"\b(?:не|никогда не) (?:(?:прода|переда|раскрыва|предоставля|распространя|разглаша)(?:[её]м|[её]т|ют)\b|делимся|делится)"
    r"|\bне (?:будем|будет) (?:прода|переда|раскрыва|предоставля|распространя|разглаша)"
    r"|\b(?:бер|бөліс|жария ет|сат|тарат|аш)(?:пей|бей|мей|пай|бай|май)(?:міз|мыз|ді|ды)\b",
    re.I,
)
_RECIPIENT = re.compile(r"треть\w* лиц|кому-либо|никому|партн[её]р|үшінші тұлға|ешкімге", re.I)
_QUALIFIED = re.compile(
    r"за исключением|кроме (?:случа|как|того)|\bиначе\b|если иное|\bесли\b|помимо|без (?:\w+ ){0,2}согласия"
    r"|только (?:с|в случа|при|для|в целях)|в (?:рекламных|маркетинговых|коммерческих) целях|в целях (?:рекламы|маркетинга)"
    r"|қоспағанда|келісімінсіз|\bтек\b|басқа жағдай|жағдайлардан басқа|жарнама",
    re.I,
)
# Strongest evidence first: a qualified "we do not pass data to third parties except ..." sentence names the recipients.
_PROCESSORS = (
    r"(?:переда|предоставл|раскрыва)\w* .{0,80}третьим лицам|третьим лицам .{0,40}(?:переда|предоставл)"
    r"|үшінші тұлғаларға (?:бер|беріл)",
    r"обработчик|подрядчик|поставщик\w* (?:услуг|сервис)|партн[её]р|контрагент|аффилированн|поручени\w* (?:на )?обработк"
    r"|серіктес|өңдеуші|мердігер",
)
_SELLS = re.compile(r"\bмы (?:можем )?прода|рекламодател|сатамыз|сатуымыз мүмкін|жарнама берушілер", re.I)

_RIGHTS = {
    "access": r"доступ к (?:своим|сво[её]й|его)|право на доступ|ознаком\w* с (?:своими|персональн)"
    r"|получ\w* информаци\w*.{0,60}(?:персональн|обработк)|қол жеткіз|танысу|ақпаратты алуға",
    "rectification": r"уточнени|исправлени|изменени\w* и дополнени|изменить (?:свои|персональн)|өзгертуді|толықтыруды|түзет",
    "erasure": r"удалени|уничтожени|удалить (?:свои|ваши|аккаунт|учетн|учётн)|право на забвение|\bжою",
    "restriction": r"ограничени\w* обработк|блокировани|бұғатта",
    "objection": r"отозвать (?:сво[её] )?согласие|отзыв\w* (?:сво\w* )?согласи|возраж|кері қайтарып ал|қарсылық",
    "portability": r"переносимост|машиночитаем|в структурированном",
}

_HOW = r"(?:можете|вправе|можно|необходимо|чтобы|для|аласыз|үшін)\b.{0,80}"
_DELETION = (
    r"удал\w* (?:сво\w* |ваш\w* )?(?:учетн|учётн|аккаунт|профил)|запрос\w* на удаление"
    r"|(?:аккаунт|тіркелгі|профиль)\w* жою"
)
_AI = (
    r"искусственн\w* интеллект|\bИИ\b|машинн\w* обучени|нейросет|нейронн\w* сет|языков\w* модел"
    r"|жасанды интеллект|\bЖИ\b|\bAI\b|\bLLM|ChatGPT|\bGPT"
)
_TRANSFERS = (
    r"трансграничн|за предел\w* (?:Республики Казахстан|Казахстана|РК|страны)|иностранн\w* государств"
    r"|на территори\w* (?:иностранн|других государств)"
    r"|сервер\w* .{0,60}(?:США|Европ|Германи|Нидерланд|Ирланди|Финлянди|Росси)"
    r"|трансшекаралық|шет мемлекет|шетелге|шетелдік|Қазақстан Республикасынан тыс"
)
_RETENTION = (
    r"(?:хран|сохран)\w*.{0,80}(?:срок|в течение|до достижения|до момента|лет\b|месяц|дней|пока)|срок\w* (?:хранени|обработки)"
    r"|сақта\w*.{0,80}(?:мерзім|жыл|\bай\b|күн)|сақтау мерзім"
)
_COOKIE_CONSENT = r"(?:cookie|куки).{0,120}(?:соглас|келісім)|(?:соглас|келісім).{0,120}(?:cookie|куки)"


def is_cyrillic(text: str) -> bool:
    letters = len(_LETTER.findall(text))
    return letters > 0 and len(_CYRILLIC.findall(text)) / letters >= 0.2


def sentences(text: str) -> list[str]:
    """Split only before a capital letter or digit, so "в т.ч. полученные" stays one sentence."""
    parts = re.split(r"(?<=[.!?])\s+(?=[А-ЯЁӘҒҚҢӨҰҮҺІA-Z0-9«\"(—–-])|\n+", text)
    return [s for s in (re.sub(r"\s+", " ", p).strip() for p in parts) if len(s) > 15]


def heuristic(policy_text: str) -> PolicyClaims:
    sents = sentences(policy_text)
    quotes: dict[str, str] = {}

    def find(key: str, pattern: str) -> bool:
        rx = re.compile(pattern, re.I)
        hit = next((s for s in sents if rx.search(s)), None)
        if hit:
            quotes.setdefault(key, hit)
        return hit is not None

    data_categories = [
        c for c, rx in _CATEGORIES.items() if find("data_categories" if c == "email" else f"data_{c}", rx)
    ]

    blanket = next(
        (s for s in sents if _NO_SHARE.search(s) and _RECIPIENT.search(s) and not _QUALIFIED.search(s)), None
    )
    if blanket:
        sharing = "no_sharing"
        quotes["sharing_statement"] = blanket
    elif any(find("sharing_statement", rx) for rx in _PROCESSORS):
        sharing = "processors_only"
    elif sells := next((s for s in sents if _SELLS.search(s) and not _NO_SHARE.search(s)), None):
        sharing = "sells_or_shares"
        quotes["sharing_statement"] = sells
    else:
        sharing = "unclear"

    rights_listed = [r for r, rx in _RIGHTS.items() if find(f"right_{r}", rx)]
    find("deletion_method", _HOW + f"(?:{_DELETION})") or find("deletion_method", _DELETION)
    return PolicyClaims(
        data_categories=data_categories,
        named_processors=[],
        sharing_statement=sharing,
        mentions_ai=find("mentions_ai", _AI),
        international_transfers=find("international_transfers", _TRANSFERS),
        retention_stated=find("retention_stated", _RETENTION),
        rights_listed=rights_listed,
        deletion_method=quotes.get("deletion_method"),
        cookie_consent_described=find("cookie_consent_described", _COOKIE_CONSENT),
        quotes=quotes,
    )


def merge(en: PolicyClaims, local: PolicyClaims) -> PolicyClaims:
    """Union of what the English and Russian/Kazakh heuristics found; English wins where both found something."""
    return PolicyClaims(
        data_categories=list(dict.fromkeys(en.data_categories + local.data_categories)),
        named_processors=list(dict.fromkeys(en.named_processors + local.named_processors)),
        sharing_statement=local.sharing_statement if en.sharing_statement == "unclear" else en.sharing_statement,
        mentions_ai=en.mentions_ai or local.mentions_ai,
        international_transfers=en.international_transfers or local.international_transfers,
        retention_stated=en.retention_stated or local.retention_stated,
        rights_listed=list(dict.fromkeys(en.rights_listed + local.rights_listed)),
        deletion_method=en.deletion_method or local.deletion_method,
        cookie_consent_described=en.cookie_consent_described or local.cookie_consent_described,
        quotes={**local.quotes, **en.quotes},
    )  # fmt: skip
