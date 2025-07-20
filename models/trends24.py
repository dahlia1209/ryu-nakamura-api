from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import json
import uuid
from azure.data.tables import TableEntity



class TrendItem(BaseModel):
    """個別のトレンド項目"""

    text: str = Field(..., description="トレンドのテキスト")
    url: HttpUrl = Field(..., description="TwitterのトレンドURL")
    tweet_count: Optional[str] = Field(None, description="ツイート数（表示用文字列）")
    tweet_count_raw: Optional[int] = Field(None, description="ツイート数（数値）")

    class Config:
        json_encoders = {HttpUrl: str}


class TimelineTrend(BaseModel):
    """タイムライン上の特定時刻のトレンドデータ"""

    timestamp: Optional[str] = Field(None, description="タイムスタンプ（UNIX時間）")
    timestamp_text: str = Field(..., description="タイムスタンプ（表示用テキスト）")
    trends: List[TrendItem] = Field(
        default_factory=list, description="その時刻のトレンドリスト"
    )

    @field_validator("timestamp")
    def validate_timestamp(cls, v):
        if v is not None:
            try:
                # UNIX timestampかどうか確認
                float(v)
            except (ValueError, TypeError):
                raise ValueError("timestampは数値である必要があります")
        return v


class StatItem(BaseModel):
    """統計項目"""

    trend: str = Field(..., description="トレンド名")
    url: HttpUrl = Field(..., description="TwitterのトレンドURL")
    info: str = Field(..., description="追加情報（期間、ツイート数など）")

    class Config:
        json_encoders = {HttpUrl: str}


class StatCategory(BaseModel):
    """統計カテゴリ"""

    title: str = Field(..., description="カテゴリタイトル")
    items: List[StatItem] = Field(default_factory=list, description="統計項目リスト")


class TrendsStatistics(BaseModel):
    """トレンド統計データ"""

    longest_trending: Optional[StatCategory] = Field(None, description="最長トレンド")
    max_tweets: Optional[StatCategory] = Field(None, description="最大ツイート数")
    new_trends: Optional[StatCategory] = Field(None, description="新しいトレンド")
    popular_active: Optional[StatCategory] = Field(
        None, description="人気のアクティブトレンド"
    )


class Trends24Data(BaseModel):
    """trends24.inから取得される全データ"""

    timeline: List[TimelineTrend] = Field(
        default_factory=list, description="タイムライン形式のトレンドデータ"
    )
    statistics: TrendsStatistics = Field(
        default_factory=TrendsStatistics, description="統計データ"
    )
    scraped_at: datetime = Field(
        default_factory=datetime.now, description="データ取得日時"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# より詳細な統計データ用のモデル
class TrendAnalytics(BaseModel):
    """トレンドの詳細分析データ"""

    rank: Optional[int] = Field(None, description="順位")
    peak_position: Optional[int] = Field(None, description="最高順位")
    duration_hours: Optional[float] = Field(
        None, description="トレンド継続時間（時間）"
    )
    total_tweets: Optional[int] = Field(None, description="総ツイート数")
    trend_velocity: Optional[float] = Field(
        None, description="トレンド速度（ツイート/時間）"
    )


class EnhancedTrendItem(TrendItem):
    """拡張トレンド項目（分析データ付き）"""

    analytics: Optional[TrendAnalytics] = Field(None, description="分析データ")
    hashtags: List[str] = Field(default_factory=list, description="関連ハッシュタグ")
    category: Optional[str] = Field(
        None, description="カテゴリ（エンタメ、スポーツなど）"
    )


# データ検証用のバリデーター関数
class DataValidator:
    """データ検証用クラス"""

    @staticmethod
    def validate_trends24_data(data: Dict[str, Any]) -> Trends24Data:
        """辞書データをPydanticモデルに変換・検証"""
        try:
            return Trends24Data(**data)
        except Exception as e:
            raise ValueError(f"データ検証エラー: {e}")

    @staticmethod
    def validate_timeline_data(
        timeline_data: List[Dict[str, Any]],
    ) -> List[TimelineTrend]:
        """タイムラインデータの検証"""
        validated_data = []
        for item in timeline_data:
            try:
                validated_data.append(TimelineTrend(**item))
            except Exception as e:
                print(f"タイムラインデータ検証エラー: {e}, データ: {item}")
                continue
        return validated_data


# 使用例とヘルパー関数
class Trends24DataProcessor:
    """Trends24データの処理クラス"""

    @staticmethod
    def create_from_scraper_output(scraper_data: Dict[str, Any]) -> Trends24Data:
        """スクレイパーの出力からPydanticモデルを作成"""
        return Trends24Data(**scraper_data)

    @staticmethod
    def get_top_trends(data: Trends24Data, limit: int = 10) -> List[TrendItem]:
        """上位トレンドを取得"""
        if not data.timeline:
            return []
        return data.timeline[0].trends[:limit]

    @staticmethod
    def get_trends_by_timeframe(data: Trends24Data, hours_ago: int) -> List[TrendItem]:
        """指定時間前のトレンドを取得"""
        if len(data.timeline) <= hours_ago:
            return []
        return data.timeline[hours_ago].trends

    @staticmethod
    def find_trending_hashtags(data: Trends24Data) -> List[str]:
        """すべてのハッシュタグを抽出"""
        hashtags = set()
        for timeline in data.timeline:
            for trend in timeline.trends:
                if trend.text.startswith("#"):
                    hashtags.add(trend.text)
        return list(hashtags)

    @staticmethod
    def calculate_trend_statistics(data: Trends24Data) -> Dict[str, Any]:
        """トレンドの統計情報を計算"""
        all_trends = []
        for timeline in data.timeline:
            all_trends.extend(timeline.trends)

        total_trends = len(all_trends)
        hashtag_count = len([t for t in all_trends if t.text.startswith("#")])

        # ツイート数の統計
        tweet_counts = [
            t.tweet_count_raw for t in all_trends if t.tweet_count_raw is not None
        ]

        stats = {
            "total_unique_trends": len(set(t.text for t in all_trends)),
            "total_trend_occurrences": total_trends,
            "hashtag_ratio": hashtag_count / total_trends if total_trends > 0 else 0,
            "timeline_count": len(data.timeline),
        }

        if tweet_counts:
            stats.update(
                {
                    "avg_tweet_count": sum(tweet_counts) / len(tweet_counts),
                    "max_tweet_count": max(tweet_counts),
                    "min_tweet_count": min(tweet_counts),
                }
            )

        return stats


class Trends24DataTableEntity(BaseModel):
    PartitionKey: str
    RowKey: str
    category: str
    trend: str
    rank: int
    url: str
    info: str
    scraped_at: str

    @classmethod
    def from_trends24_data(
        cls,
        trends24: Trends24Data,
    ):
        entities: List[Trends24DataTableEntity] = []

        longItems = [
            item
            for item in trends24.statistics.longest_trending.items
            if trends24.statistics.longest_trending
        ]
        maxItems = [
            item
            for item in trends24.statistics.max_tweets.items
            if trends24.statistics.max_tweets
        ]
        newItems = [
            item
            for item in trends24.statistics.new_trends.items
            if trends24.statistics.new_trends
        ]
        popuItems = [
            item
            for item in trends24.statistics.popular_active.items
            if trends24.statistics.popular_active
        ]
        
        yyyyMMddHH=trends24.scraped_at.strftime("%Y%m%d%H")

        for i,items in enumerate([longItems, maxItems, newItems, popuItems]):
            category=['longest_trending', 'max_tweets', 'new_trends', 'popular_active'][i]
            for j,item in enumerate(items):
                rank=j+1
                entity=Trends24DataTableEntity.from_trends24_item(item,rank,category,trends24.scraped_at,yyyyMMddHH)
                entities.append(entity)

        return entities

    @classmethod
    def from_trends24_item(
        cls,
        item: StatItem,
        rank: int,
        category: str,
        scraped_at: datetime,
        PartitionKey: str = None,
        RowKey: str = None,
    ):
        if PartitionKey is None:
            PartitionKey = datetime.now(timezone.utc).isoformat()
        
        if RowKey is None:
            RowKey = str(uuid.uuid4())

        return cls(
            PartitionKey=PartitionKey,
            RowKey=RowKey,
            rank=rank,
            scraped_at=scraped_at.isoformat(),
            category=category,
            trend=item.trend,
            url=str(item.url),
            info=item.info,
        )
        
    @classmethod
    def from_entity(cls, entity: TableEntity) :
        entity_dict = dict(entity)
        table_entity = Trends24DataTableEntity.model_validate(entity_dict)
        return table_entity
        

