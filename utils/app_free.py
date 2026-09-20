import os


def app_free_title_nos() -> set[int]:
    """WebのStripe価格とは無関係に、アプリ内でのみ無料公開する記事番号の一覧"""
    raw = os.getenv("APP_FREE_TITLE_NOS", "")
    return {int(part) for part in raw.split(",") if part.strip().isdigit()}
