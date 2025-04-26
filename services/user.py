from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from typing import List, Optional,Literal
from models.user import User
from repository import user as user_repo
from datetime import datetime
from api.auth import get_current_user, requires_scope
from models.query import QueryFilter
import uuid

