# src/person_api.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import base64
import cv2
import numpy as np

from logger_utils import get_logger
from person_manager import PersonManager
# ===== 日志 =====
logger = get_logger('person_api')

# ===== 创建路由器 =====
router = APIRouter(prefix="/api/persons", tags=["人员管理"])

# ===== 初始化人员管理器 =====
person_manager = PersonManager(db_path="fall_events.db", photo_dir="data/photos")


# ===== Pydantic 模型 =====

class PersonCreate(BaseModel):
    name: str
    age: Optional[int] = None
    gender: str = "未知"
    room_number: Optional[str] = None
    bed_number: Optional[str] = None
    floor: Optional[str] = None
    building: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_relationship: Optional[str] = None
    medical_history: Optional[str] = None
    special_notes: Optional[str] = None
    photo_base64: Optional[str] = None


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    room_number: Optional[str] = None
    bed_number: Optional[str] = None
    floor: Optional[str] = None
    building: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_relationship: Optional[str] = None
    medical_history: Optional[str] = None
    special_notes: Optional[str] = None
    photo_base64: Optional[str] = None
    status: Optional[int] = None


class PersonResponse(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    gender: str
    room_number: Optional[str] = None
    bed_number: Optional[str] = None
    floor: Optional[str] = None
    building: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_relationship: Optional[str] = None
    medical_history: Optional[str] = None
    special_notes: Optional[str] = None
    photo_path: Optional[str] = None
    photo_base64: Optional[str] = None
    status: int
    created_at: str
    updated_at: str


# ===== 辅助函数 =====

def decode_photo(photo_base64: Optional[str]) -> Optional[np.ndarray]:
    """解码 Base64 图片为 OpenCV 图像"""
    if not photo_base64:
        return None

    try:
        img_data = base64.b64decode(photo_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        logger.warning(f"照片解码失败: {e}")
        return None


def enrich_person_with_photo(person: Dict[str, Any]) -> Dict[str, Any]:
    """为人员信息添加照片 Base64"""
    result = dict(person)
    if person.get('photo_path'):
        photo_base64 = person_manager.get_photo_base64(person['photo_path'])
        result['photo_base64'] = photo_base64
    return result




# ===== API 端点 =====

@router.post("", response_model=Dict[str, Any])
async def create_person(person: PersonCreate):
    """
    创建人员
    """
    try:
        # 解码照片
        photo_img = decode_photo(person.photo_base64)

        # 准备数据
        person_data = person.dict(exclude={'photo_base64'})

        # 添加人员
        person_id = person_manager.add_person(person_data, photo_img)

        logger.info(f"人员创建成功: {person.name} (ID: {person_id})")

        return {
            "status": "success",
            "message": f"人员 {person.name} 创建成功",
            "person_id": person_id
        }

    except Exception as e:
        logger.error(f"创建人员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=Dict[str, Any])
async def get_persons(
        limit: int = Query(100, description="返回数量"),
        offset: int = Query(0, description="偏移量"),
        search: Optional[str] = Query(None, description="搜索关键词")
):
    """
    获取人员列表
    """
    try:
        if search:
            persons = person_manager.search_persons(search)
        else:
            persons = person_manager.get_persons(limit=limit, offset=offset)

        # 添加照片 Base64
        enriched_persons = [enrich_person_with_photo(p) for p in persons]

        return {
            "total": len(enriched_persons),
            "limit": limit,
            "offset": offset,
            "persons": enriched_persons
        }

    except Exception as e:
        logger.error(f"获取人员列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}", response_model=Dict[str, Any])
async def get_person(person_id: int):
    """
    获取人员详情
    """
    try:
        person = person_manager.get_person(person_id)
        if not person:
            raise HTTPException(status_code=404, detail="人员不存在")

        return enrich_person_with_photo(person)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取人员详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{person_id}", response_model=Dict[str, Any])
async def update_person(person_id: int, person: PersonUpdate):
    """
    更新人员信息
    """
    try:
        # 检查人员是否存在
        existing = person_manager.get_person(person_id)
        if not existing:
            raise HTTPException(status_code=404, detail="人员不存在")

        # 解码照片
        photo_img = decode_photo(person.photo_base64)

        # 准备数据（排除空值）
        person_data = person.dict(exclude={'photo_base64'}, exclude_none=True)

        # 更新人员
        success = person_manager.update_person(person_id, person_data, photo_img)

        if not success:
            raise HTTPException(status_code=500, detail="更新失败")

        logger.info(f"人员更新成功: ID={person_id}")

        return {
            "status": "success",
            "message": f"人员 ID={person_id} 更新成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新人员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{person_id}", response_model=Dict[str, Any])
async def delete_person(person_id: int):
    """
    删除人员（软删除）
    """
    try:
        # 检查人员是否存在
        existing = person_manager.get_person(person_id)
        if not existing:
            raise HTTPException(status_code=404, detail="人员不存在")

        success = person_manager.delete_person(person_id)

        if not success:
            raise HTTPException(status_code=500, detail="删除失败")

        logger.info(f"人员删除成功: ID={person_id}")

        return {
            "status": "success",
            "message": f"人员 ID={person_id} 删除成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除人员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{person_id}/permanent", response_model=Dict[str, Any])
async def delete_person_permanently(person_id: int):
    """
    永久删除人员（同时删除照片）
    """
    try:
        # 检查人员是否存在
        existing = person_manager.get_person(person_id)
        if not existing:
            raise HTTPException(status_code=404, detail="人员不存在")

        success = person_manager.delete_person_permanently(person_id)

        if not success:
            raise HTTPException(status_code=500, detail="删除失败")

        logger.info(f"人员永久删除成功: ID={person_id}")

        return {
            "status": "success",
            "message": f"人员 ID={person_id} 已永久删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"永久删除人员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=Dict[str, Any])
async def get_person_statistics():
    """
    获取人员统计信息
    """
    try:
        stats = person_manager.get_statistics()
        return stats

    except Exception as e:
        logger.error(f"获取人员统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=Dict[str, Any])
async def search_persons(
        keyword: str = Query(..., description="搜索关键词")
):
    """
    搜索人员（姓名/房间号/监护人）
    """
    try:
        persons = person_manager.search_persons(keyword)
        enriched_persons = [enrich_person_with_photo(p) for p in persons]

        return {
            "total": len(enriched_persons),
            "keyword": keyword,
            "persons": enriched_persons
        }

    except Exception as e:
        logger.error(f"搜索人员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))