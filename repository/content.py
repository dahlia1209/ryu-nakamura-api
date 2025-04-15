from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from managers.table_connection import TableConnectionManager
from models.content import Content,ContentTableEntity
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid

# クライアントとテーブルの初期化関数
def get_table_client():
    try:
        manager = TableConnectionManager()
        client=manager.client
        
        # テーブルが存在するか確認し、なければ作成
        try:
            table_client = client.create_table_if_not_exists("contents")
        except ResourceExistsError:
            table_client = client.get_table_client("contents")
            
        return table_client
    except Exception as e:
        raise Exception(f"Error connecting to Azure Table Storage: {str(e)}")
        

def get_contents(
        category: Optional[str] = None, 
        title_no:Optional[int]=None,
        limit: int = 50,
        is_preview:bool=False
    ) -> List[Content]:

    try:
        table_client = get_table_client()
        query_parts = []
        
        if category:
            query_parts.append(f"PartitionKey eq '{category}'")
        if title_no:
            query_parts.append(f"title_no eq {title_no}")
            
        query = " and ".join(query_parts) if query_parts else None
        
        entities = list(table_client.query_entities(query, results_per_page=limit))
        contents = []
        
        for entity in entities:
            # Tagsが文字列として保存されている場合、リストに変換
            if isinstance(entity.get('tags'), str):
                entity['tags'] = json.loads(entity['tags'])
                
            # 日付が文字列の場合、datetimeに変換
            if isinstance(entity.get('publish_date'), str):
                entity['publish_date'] = datetime.fromisoformat(entity['publish_date'])
            
            try:
                # エンティティモデルを使用して変換
                table_entity = ContentTableEntity(
                    PartitionKey=entity.get('PartitionKey', ''),
                    RowKey=entity.get('RowKey', ''),
                    title_no=entity.get('title_no',0),
                    title=entity.get('title'),
                    content_text=entity.get('content_text'),
                    content_html=entity.get('content_html'),
                    image_url=entity.get('image_url'),
                    price=entity.get('price'),
                    tags=entity.get('tags'),
                    publish_date=entity.get('publish_date'),
                    preview_text_length=entity.get('preview_text_length'),
                    note_url=entity.get('note_url')
                )
                
                # エンティティからContentモデルに変換
                content = table_entity.to_content()
                contents.append(content)
            except Exception as validation_error:
                print(f"Validation error for entity {entity.get('RowKey')}: {str(validation_error)}")
                # エラーが発生したエンティティをスキップ
                continue
            
        return contents
    except Exception as e:
        print(f"Error retrieving contents: {str(e)}")
        return []

def create_or_update_content(content: Content) -> bool:
    """コンテンツの作成または更新"""
    try:
        table_client = get_table_client()
        
        content_entity=ContentTableEntity.from_content(content)
        
        entity_dict = content_entity.model_dump(exclude_none=True)
        
         # タグがリストの場合、JSON文字列に変換
        if 'tags' in entity_dict and isinstance(entity_dict['tags'], list):
            entity_dict['tags'] = json.dumps(entity_dict['tags'])
            
        # datetimeオブジェクトをISO形式文字列に変換
        if 'publish_date' in entity_dict and isinstance(entity_dict['publish_date'], datetime):
            entity_dict['publish_date'] = entity_dict['publish_date'].isoformat()
        
        # エンティティのアップサート（存在すれば更新、なければ作成）
        table_client.upsert_entity(entity_dict)
        return True
    except Exception as e:
        print(f"Error creating/updating content: {str(e)}")
        return False

def delete_content(content_id: int) -> bool:
    """指定されたIDのコンテンツを削除する"""
    try:
        table_client = get_table_client()
        
        # IDを使用してエンティティを検索
        query = f"RowKey eq '{str(content_id)}'"
        entities = list(table_client.query_entities(query))
        
        if not entities:
            return False
            
        # 見つかったエンティティを削除
        entity = entities[0]
        table_client.delete_entity(
            partition_key=entity['PartitionKey'],
            row_key=entity['RowKey']
        )
        return True
    except Exception as e:
        print(f"Error deleting content: {str(e)}")
        return False