import json
from datetime import datetime

from models.content import Content
from utils.app_free import app_free_title_nos


def test_app_free_title_nos_parses_comma_separated_numbers(monkeypatch):
    monkeypatch.setenv("APP_FREE_TITLE_NOS", "1, 18,x, ,3")
    assert app_free_title_nos() == {1, 3, 18}


def test_app_free_title_nos_is_empty_when_unset(monkeypatch):
    monkeypatch.delenv("APP_FREE_TITLE_NOS", raising=False)
    assert app_free_title_nos() == set()


def test_preview_json_includes_is_app_free_defaulting_to_false():
    content = Content(
        title_no=1,
        title="t",
        content_text="本文",
        content_html="<h2>見出し</h2><p>本文</p>",
        image_url="https://example.com/1.webp",
        price=200,
        category="c",
        tags=[],
        publish_date=datetime(2025, 1, 1),
    )
    preview = content.to_preview()
    assert json.loads(preview.model_dump_json())["is_app_free"] is False

    preview.is_app_free = True
    assert json.loads(preview.model_dump_json())["is_app_free"] is True
