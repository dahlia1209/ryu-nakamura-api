from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from managers.table_connection import TableConnectionManager
from models.user import User, UserTableEntity
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid

# クライアントとテーブルの初期化関数
# def get_table_client():
#     try:
#         manager = TableConnectionManager()
#         client = manager.client
        
#         # テーブルが存在するか確認し、なければ作成
#         try:
#             table_client = client.create_table_if_not_exists("users")
#         except ResourceExistsError:
#             table_client = client.get_table_client("users")
            
#         return table_client
#     except Exception as e:
#         raise Exception(f"Error connecting to Azure Table Storage: {str(e)}")

def get_user_by_id(user_id: str) -> Optional[User]:
    """ユーザーIDでユーザーを取得する"""
    try:
        manager = TableConnectionManager()
        table_client = manager.user_table
        query = f"RowKey eq '{user_id}'"
        entities = list(table_client.query_entities(query))
        
        if not entities:
            return None
            
        entity = entities[0]
        
        try:
            # エンティティを辞書として取得
            entity_dict = dict(entity)
            
            # UserTableEntityへ自動変換
            # モデルのparse_obj/model_validateメソッドを使用してエンティティを変換
            table_entity = UserTableEntity.model_validate(entity_dict)
            
            # Userモデルに変換
            return table_entity.to_user()
        except Exception as e:
            print(f"Validation error for user {user_id}: {e}")
            return None
    except Exception as e:
        print(f"Error getting user by id {user_id}: {e}")
        return None


def get_user_by_email(email: str) -> Optional[User]:
    """メールアドレスでユーザーを取得する"""
    try:
        manager = TableConnectionManager()
        table_client = manager.user_table
        query = f"email eq '{email}'"
        entities = list(table_client.query_entities(query))
        
        if not entities:
            return None
            
        entity = entities[0]
        
        try:
            # テーブルエンティティモデルに変換
            table_entity = UserTableEntity(
                PartitionKey=entity.get('PartitionKey', 'User'),
                RowKey=entity.get('RowKey', ''),
                email=entity.get('email', ''),
                addresses=entity.get('addresses'),
                created_at=entity.get('created_at'),
                updated_at=entity.get('updated_at'),
                last_login=entity.get('last_login'),
                preferences=entity.get('preferences')
            )
            
            # Userモデルに変換
            return table_entity.to_user()
            
        except Exception as validation_error:
            print(f"Validation error for user with email {email}: {str(validation_error)}")
            return None
            
    except Exception as e:
        print(f"Error retrieving user by email: {str(e)}")
        return None

def get_users(limit: int = 50) -> List[User]:
    """ユーザー一覧を取得する"""
    try:
        manager = TableConnectionManager()
        table_client = manager.user_table
        entities = list(table_client.query_entities(query_filter="PartitionKey eq 'User'", results_per_page=limit))
        
        users = []
        for entity in entities:
            try:
                # テーブルエンティティモデルに変換
                table_entity = UserTableEntity(
                    PartitionKey=entity.get('PartitionKey', 'User'),
                    RowKey=entity.get('RowKey', ''),
                    email=entity.get('email', ''),
                    created_at=entity.get('created_at'),
                    updated_at=entity.get('updated_at'),
                    last_login=entity.get('last_login'),
                )
                
                # Userモデルに変換
                user = table_entity.to_user()
                users.append(user)
                
            except Exception as validation_error:
                print(f"Validation error for user {entity.get('RowKey')}: {str(validation_error)}")
                continue
                
        return users
        
    except Exception as e:
        print(f"Error retrieving users: {str(e)}")
        return []

def create_user(user: User) -> bool:
    """新しいユーザーを作成する"""
    try:
        manager = TableConnectionManager()
        table_client = manager.user_table
        
        # 現在の時刻を更新
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        
        # UserモデルをTableEntityに変換
        user_entity = UserTableEntity.from_user(user)
        
        # エンティティディクショナリに変換
        entity_dict = user_entity.model_dump(exclude_none=True)
        
        # エンティティを作成
        table_client.create_entity(entity_dict)
        return True
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return False

def update_user(user: User) -> bool:
    """ユーザーを更新する"""
    try:
        manager = TableConnectionManager()
        table_client = manager.user_table
        
        # 既存のユーザーを確認
        existing_user = get_user_by_id(user.id)
        if not existing_user:
            return False
            
        # 更新日時を現在に設定
        user.updated_at = datetime.now()
        
        # UserモデルをTableEntityに変換
        user_entity = UserTableEntity.from_user(user)
        
        # エンティティディクショナリに変換
        entity_dict = user_entity.model_dump(exclude_none=True)
        
        # エンティティを更新
        table_client.update_entity(entity_dict)
        return True
        
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return False

def update_user_login(user_id: str) -> bool:
    """ユーザーの最終ログイン時間を更新する"""
    try:
        # 既存のユーザーを取得
        user = get_user_by_id(user_id)
        if not user:
            return False
            
        # 最終ログイン時間を更新
        user.last_login = datetime.now()
        user.updated_at = datetime.now()
        
        # ユーザーを更新
        return update_user(user)
        
    except Exception as e:
        print(f"Error updating user login: {str(e)}")
        return False

def delete_user(user_id: str) -> bool:
    """ユーザーを削除する"""
    try:
        manager = TableConnectionManager()
        table_client = manager.user_table
        
        # ユーザーを取得
        user = get_user_by_id(user_id)
        if not user:
            return False
            
        # エンティティを削除
        table_client.delete_entity(
            partition_key="User",
            row_key=user.id
        )
        return True
        
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return False