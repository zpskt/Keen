# src/routers/events.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
import base64
import os
from typing import Optional

from src.util.logger_utils import get_logger
from src.database.fall_events_manager import Database
from src.util.oss_utils import OSSClient
from src.util.wechat_work_utils import WeChatWorkNotifier

logger = get_logger('events_router')
router = APIRouter(tags=["事件管理"])

# ===== 初始化 =====
db = Database(db_path="fall_events.db")
oss_client = OSSClient(bucket_name="fall-detection-dev", region="cn-beijing")
notifier = WeChatWorkNotifier()


# ===== 请求模型 =====
class FallEvent(BaseModel):
    timestamp: str
    event_type: str
    source: str
    image_base64: str
    metadata: dict


# ===== 事件接收 =====
@router.post("/fall-events")
async def receive_fall_event(event: FallEvent):
    """
    接收跌倒事件，处理并存储
    """
    try:
        logger.info(f"📨 收到事件: {event.event_type} from {event.source} at {event.timestamp}")
        logger.debug(f"元数据: {event.metadata}")

        img_data = base64.b64decode(event.image_base64)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

        upload_result = oss_client.upload_image(event.image_base64, prefix="fall-events")

        image_url = None
        image_key = None

        if upload_result["success"]:
            image_url = upload_result["image_url"]
            image_key = upload_result["object_key"]
            logger.info(f"✅ 图片上传成功: {image_url}")
        else:
            logger.warning(f"⚠️ 图片上传失败: {upload_result['error']}")
            local_path = f"fallback_images/fall_{timestamp_str}.jpg"
            os.makedirs("fallback_images", exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(img_data)
            image_url = f"file://{os.path.abspath(local_path)}"
            image_key = local_path
            logger.info(f"💾 图片已保存到本地: {image_url}")

        event_data = {
            'event_type': event.event_type,
            'source': event.source,
            'event_time': event.timestamp,
            'received_time': datetime.now().isoformat(),
            'confidence': event.metadata.get('confidence', 0.0),
            'image_url': image_url,
            'image_key': image_key,
            'image_bucket': "fall-detection-dev",
            'image_region': "cn-beijing",
            'metadata': event.metadata,
            'status': 0,
            'remark': f"从 {event.source} 接收"
        }

        event_id = db.insert_event(event_data)
        logger.info(f"💾 事件已存储到数据库, ID: {event_id}")

        if notifier:
            notification_result = notifier.send_fall_alert_notification(
                event_data=event_data,
                event_id=event_id,
                image_url=image_url
            )

            if notification_result and notification_result.get('success'):
                logger.info(f"📱 企业微信通知发送成功，事件ID: {event_id}")
                db.mark_notification_sent(event_id)
            else:
                logger.warning(f"⚠️ 企业微信通知发送失败: {notification_result.get('message', '未知错误')}")

        return {
            "status": "success",
            "message": "事件已接收并存储",
            "event_id": event_id,
            "image_url": image_url
        }

    except Exception as e:
        logger.exception(f"❌ 处理事件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.get("/events/statistics")
async def get_statistics():
    """获取事件统计信息"""
    try:
        stats = db.get_statistics()
        logger.debug(f"统计信息查询成功: {stats}")
        return stats
    except Exception as e:
        logger.error(f"查询统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询统计信息失败")


@router.get("/events")
async def get_events(
        limit: int = Query(100, description="返回数量"),
        offset: int = Query(0, description="偏移量"),
        event_type: Optional[str] = Query(None, description="过滤事件类型")
):
    """获取所有已接收的事件"""
    try:
        events = db.get_events(limit=limit, offset=offset, event_type=event_type)
        logger.debug(f"查询事件列表: limit={limit}, offset={offset}, type={event_type}, count={len(events)}")
        return {
            "total": len(events),
            "limit": limit,
            "offset": offset,
            "events": events
        }
    except Exception as e:
        logger.error(f"查询事件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询事件列表失败")


@router.get("/events/{event_id}")
async def get_event(event_id: int):
    """获取单个事件的详细信息"""
    try:
        event = db.get_event(event_id)
        if not event:
            logger.warning(f"事件不存在: event_id={event_id}")
            raise HTTPException(status_code=404, detail="事件不存在")
        logger.debug(f"查询事件详情: event_id={event_id}")
        return event
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询事件详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询事件详情失败")


@router.patch("/events/{event_id}/status")
async def update_event_status(event_id: int, status: int):
    """
    更新事件状态
    status: 0-待处理, 1-处理中, 2-已完成, 3-失败
    """
    if status not in [0, 1, 2, 3]:
        logger.warning(f"无效的状态值: {status}")
        raise HTTPException(status_code=400, detail="无效的状态值")

    try:
        success = db.update_event_status(event_id, status)
        if not success:
            logger.warning(f"事件不存在: event_id={event_id}")
            raise HTTPException(status_code=404, detail="事件不存在")

        logger.info(f"事件状态更新成功: event_id={event_id}, status={status}")
        return {"status": "success", "message": f"事件 {event_id} 状态已更新为 {status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新事件状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新事件状态失败")