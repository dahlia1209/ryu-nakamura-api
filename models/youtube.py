from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import json
from azure.data.tables import TableEntity

class Thumbnail(BaseModel):
    url: str
    width: int
    height: int


class ThumbnailCollection(BaseModel):
    default: Optional[Thumbnail] = None
    medium: Optional[Thumbnail] = None
    high: Optional[Thumbnail] = None
    standard: Optional[Thumbnail] = None
    maxres: Optional[Thumbnail] = None


class Localized(BaseModel):
    title: str
    description: str


class VideoSnippet(BaseModel):
    publishedAt: datetime = Field(alias="publishedAt")
    channelId: str
    title: str
    description: str
    thumbnails: ThumbnailCollection
    channelTitle: str
    tags: List[str] = []
    categoryId: str
    liveBroadcastContent: str
    localized: Optional[Localized] = None
    defaultAudioLanguage: Optional[str] = None


class VideoStatistics(BaseModel):
    viewCount: str
    likeCount: Optional[str] = None
    favoriteCount: Optional[str] = None
    commentCount: Optional[str] = None


class YouTubeVideo(BaseModel):
    kind: str
    etag: str
    id: str
    snippet: VideoSnippet
    statistics: VideoStatistics


class PageInfo(BaseModel):
    totalResults: int
    resultsPerPage: int


class YouTubeVideoListResponse(BaseModel):
    kind: str
    etag: str
    items: List[YouTubeVideo]
    nextPageToken: Optional[str] = None
    pageInfo: PageInfo


class YouTubeVideoFormat(BaseModel):
    PartitionKey: str
    id: str
    published_at: datetime
    channel_id: str
    title: str
    description: str
    thumbnail_url: str
    channel_title: str
    tags: List[str]=[]
    category_id: str
    live_broadcast_content: str
    default_language: Optional[str]=None
    default_audio_language: Optional[str]=None
    view_count: int
    like_count: Optional[int]=None
    favorite_count: Optional[int]=None
    comment_count: Optional[int]=None
    url: str
    rank:int
    
class YouTubeVideoTableEntity(BaseModel):
    PartitionKey: str
    RowKey: str
    published_at: str
    channel_id: str
    title: str
    description: str
    thumbnail_url: str
    channel_title: str
    tags: Optional[str]=None
    category_id: str
    live_broadcast_content: str
    default_language: Optional[str]=None
    default_audio_language: Optional[str]=None
    view_count: int
    like_count: Optional[int]=None
    favorite_count: Optional[int]=None
    comment_count: Optional[int]=None
    url: str
    rank:int

    def to_youtube_video_format(self) :
        deserialized_tags= json.loads(self.tags)  
        deserialized_published_at=datetime.fromisoformat(self.published_at)
        return YouTubeVideoFormat(tags=deserialized_tags,published_at=deserialized_published_at,id=self.RowKey,
                       **self.model_dump(exclude={"RowKey","tags","published_at"}))

    @classmethod
    def from_youtube_video(
        cls, youtube: YouTubeVideo, rank:int,PartitionKey: str = datetime.now(timezone.utc).isoformat()
    ):
        PartitionKey = PartitionKey
        RowKey = youtube.id
        url = f"https://www.youtube.com/watch?v={youtube.id}"
        published_at = youtube.snippet.publishedAt.isoformat()
        channel_id = youtube.snippet.channelId
        title = youtube.snippet.title
        description = youtube.snippet.description
        thumbnail_url = youtube.snippet.thumbnails.default.url
        channel_title = youtube.snippet.channelTitle
        tags = json.dumps(youtube.snippet.tags, ensure_ascii=False) if youtube.snippet.tags else "[]"
        category_id = str(youtube.snippet.categoryId)
        live_broadcast_content = youtube.snippet.liveBroadcastContent
        default_language = youtube.snippet.defaultAudioLanguage
        default_audio_language = youtube.snippet.defaultAudioLanguage
        view_count = youtube.statistics.viewCount
        like_count = youtube.statistics.likeCount
        favorite_count = youtube.statistics.favoriteCount
        comment_count = youtube.statistics.commentCount

        return cls(
            PartitionKey=PartitionKey,
            RowKey=RowKey,
            published_at=published_at,
            url=url,
            channel_id=channel_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            channel_title=channel_title,
            tags=tags,
            category_id=category_id,
            live_broadcast_content=live_broadcast_content,
            default_language=default_language,
            default_audio_language=default_audio_language,
            view_count=view_count,
            like_count=like_count,
            favorite_count=favorite_count,
            comment_count=comment_count,
            rank=rank
        )
        
    @classmethod
    def from_entity(cls, entity: TableEntity) :
        entity_dict = dict(entity)
        table_entity = YouTubeVideoTableEntity.model_validate(entity_dict)
        return table_entity
        
