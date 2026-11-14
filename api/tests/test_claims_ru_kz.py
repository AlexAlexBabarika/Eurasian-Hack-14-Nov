"""Russian and Kazakh policies: most Kazakhstan products publish their policy in Russian, some in Kazakh."""

from app.claims import ru_kz
from app.claims.extract import _heuristic_en, heuristic, validate_quotes
from app.detect.code_signals import CodeSignals
from app.diff.rules import run_rules
from app.models import Evidence, Observation

RU_POLICY = """Политика конфиденциальности
Мы собираем ваше имя, адрес электронной почты, номер телефона и IP-адрес, а также сведения об использовании сервиса.
Мы не передаём ваши персональные данные третьим лицам.
Ваши данные хранятся на серверах в Республике Казахстан в течение трёх лет после удаления аккаунта.
Вы вправе требовать уточнения, блокирования или уничтожения своих персональных данных, а также отозвать своё согласие.
Чтобы удалить свою учетную запись, откройте Настройки и нажмите «Удалить аккаунт».
Файлы cookie для аналитики устанавливаются только с вашего согласия."""

KZ_POLICY = """Құпиялылық саясаты
Біз сіздің аты-жөніңізді, электрондық пошта мекенжайыңызды және телефон нөміріңізді жинаймыз.
Біз сіздің дербес деректеріңізді үшінші тұлғаларға бермейміз.
Сұрауларыңызға жауап беру үшін жасанды интеллект қолданылады.
Дербес деректерді сақтау мерзімі – тіркелгі жабылғаннан кейін бір жыл.
Сіз өз дербес деректеріңізді өзгертуді, толықтыруды, бұғаттауды және жоюды талап етуге құқылысыз.
Тіркелгіні жою үшін қолдау қызметіне жазыңыз."""


def obs(vendor: str) -> Observation:
    ev = [Evidence(kind="manifest", summary="dep", file="package.json", line=1)]
    return Observation(id=f"o-{vendor}", vendor=vendor, vendor_country="US", data_categories=["email"],
                       purpose_guess="analytics", evidence=ev)  # fmt: skip


def test_russian_policy_claims():
    c = heuristic(RU_POLICY)
    assert c.sharing_statement == "no_sharing"
    assert c.quotes["sharing_statement"] == "Мы не передаём ваши персональные данные третьим лицам."
    assert {"email", "name", "phone", "ip", "usage"} <= set(c.data_categories)
    assert {"rectification", "restriction", "erasure", "objection"} <= set(c.rights_listed)
    assert c.retention_stated and c.cookie_consent_described
    assert c.deletion_method and c.deletion_method.startswith("Чтобы удалить свою учетную запись")
    assert not c.mentions_ai and not c.international_transfers


def test_kazakh_policy_claims():
    c = heuristic(KZ_POLICY)
    assert c.sharing_statement == "no_sharing"
    assert {"email", "name", "phone"} <= set(c.data_categories)
    assert c.mentions_ai and c.retention_stated
    assert {"rectification", "restriction", "erasure"} <= set(c.rights_listed)
    assert c.deletion_method == "Тіркелгіні жою үшін қолдау қызметіне жазыңыз."


def test_quotes_are_exact_policy_sentences():
    for text in (RU_POLICY, KZ_POLICY):
        c = heuristic(text)
        assert validate_quotes(c.model_copy(deep=True), text).quotes == c.quotes


def test_qualified_or_user_obligation_sentences_are_not_no_sharing():
    qualified = "Мы не передаем третьим лицам ваши данные, за исключением случаев, предусмотренных законом."
    assert heuristic(qualified).sharing_statement == "processors_only"
    assert (
        heuristic("Мы не передаём данные третьим лицам без вашего согласия.").sharing_statement
        != "no_sharing"
    )
    assert (
        heuristic("Вы обязуетесь не передавать свой пароль третьим лицам.").sharing_statement != "no_sharing"
    )
    assert heuristic("Біз заңда көзделген жағдайларды қоспағанда, деректерді үшінші тұлғаларға бермейміз.")\
        .sharing_statement != "no_sharing"  # fmt: skip


def test_abbreviations_do_not_split_the_sentence():
    text = "Мы не передаем третьим лицам ваши данные, в т.ч. полученные через приложение, за исключением партнёров."
    c = heuristic(text)
    assert c.sharing_statement == "processors_only" and c.quotes["sharing_statement"] == text


def test_transfers_and_ai_in_russian():
    c = heuristic(
        "Возможна трансграничная передача данных на серверы в США. Ответы готовит искусственный интеллект."
    )
    assert c.international_transfers and c.mentions_ai


def test_russian_no_sharing_claim_drives_the_contradiction_rule():
    findings = run_rules([obs("Mixpanel")], heuristic(RU_POLICY), CodeSignals(), "https://x.kz/privacy")
    rules = {f.rule.split("_")[0] for f in findings}
    assert "R2" in rules and "R9" not in rules and "R7" not in rules


def test_english_policies_are_unchanged():
    en = (
        "We never share your data with third parties. We keep account data for two years and you can delete your "
        "account in Settings. Our registered office: ТОО Ромашка, Алматы."
    )
    assert not ru_kz.is_cyrillic(en)
    assert heuristic(en) == _heuristic_en(en)
    assert ru_kz.is_cyrillic(RU_POLICY) and ru_kz.is_cyrillic(KZ_POLICY)


def test_bilingual_policy_merges_both_languages():
    text = "We use Stripe for payments.\n" + RU_POLICY
    c = heuristic(text)
    assert "Stripe" in c.named_processors and c.sharing_statement == "no_sharing" and c.deletion_method
