"""Tests for the parts that keep the agent safe and the page parsing honest; no browser needed."""

import pytest

from avito_mcp.browser import AvitoError, host_allowed, normalize_url
from avito_mcp.server import RISKY, _section, _snapshot_line, _text_sections


@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://www.avito.ru/profile", True),
        ("https://m.avito.ru/item", True),
        ("https://avito.ru/", True),
        ("https://evil-avito.ru/", False),
        ("https://avito.ru.evil.com/", False),
        ("https://example.com/?u=avito.ru", False),
    ],
)
def test_host_allowed(url, ok):
    assert host_allowed(url) is ok


def test_normalize_url_paths_and_scheme():
    assert normalize_url("/profile") == "https://www.avito.ru/profile"
    assert normalize_url("www.avito.ru/favorites") == "https://www.avito.ru/favorites"
    assert normalize_url("http://www.avito.ru/x") == "https://www.avito.ru/x"
    with pytest.raises(AvitoError):
        normalize_url("https://google.com")
    with pytest.raises(AvitoError):
        normalize_url("  ")


@pytest.mark.parametrize(
    "label",
    ["Отправить", "Опубликовать", "Удалить навсегда", "Оплатить", "Сохранить изменения", "Снять с публикации",
     "Показать телефон", "Купить", "В архив"],
)
def test_risky_controls_need_confirmation(label):
    assert RISKY.search(label)


@pytest.mark.parametrize("label", ["Найти", "Добавить", "Изменить", "Пропустить", "Архив 1", "Написать", "Ещё"])
def test_safe_controls_do_not(label):
    assert not RISKY.search(label)


def test_snapshot_line_is_compact():
    line = _snapshot_line({"ref": "e5", "tag": "a", "name": "Разместить объявление", "href": "/additem",
                           "marker": "header/add", "offscreen": True})
    assert line == "e5 a 'Разместить объявление' → /additem #header/add offscreen"


PAGE = """Описание шапки
Подробности
Опыт работы: 4–7 лет
Прайс-лист
Плазмолифтинг
3 000 ₽
Курс, 5 процедур
18 000 ₽
Образование, курсы
лечебное дело · 2020 г.
Описание
Текст
Статистика за 7 дней
Показы
104
Просмотры
20
Документы проверены
"""


def test_text_sections_price_list_details_and_stats():
    out = _text_sections(PAGE, {"price_list": [], "params": ""})
    assert out["price_list"] == ["Плазмолифтинг — 3 000 ₽", "Курс, 5 процедур — 18 000 ₽"]
    assert out["params"] == "Опыт работы: 4–7 лет"
    assert out["owner_stats_7d"] == "Показы 104 Просмотры 20"


def test_section_missing_returns_empty():
    assert _section(PAGE, "Отзывы", ("Описание",)) == ""
