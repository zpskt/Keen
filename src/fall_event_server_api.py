# fall_event_server_api.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse  # 改用 StreamingResponse
from pydantic import BaseModel
from datetime import datetime
import base64
import uvicorn
import os
from typing import Optional

from oss_utils import OSSClient
from db_utils import Database
from wechat_work_utils import WeChatWorkNotifier
from logger_utils import get_logger  # 新增
from person_api import router as person_router  # 导入人员管理路由
from report_api import router as report_router  # 导入报表路由
# ===== 初始化日志 =====
logger = get_logger('fall_event_server')


# ===== 定义请求体模型 =====
class FallEvent(BaseModel):
    timestamp: str
    event_type: str
    source: str
    image_base64: str
    metadata: dict


# ===== 创建FastAPI应用 =====
app = FastAPI(title="跌倒事件接收服务", description="接收跌倒检测事件并触发后续动作", version="1.0")

# ===== 挂载人员管理路由 =====
# 所有人员管理 API 都在 /api/persons 下
app.include_router(person_router)
# 挂载报表路由
app.include_router(report_router)
# ===== 初始化数据库和OSS客户端 =====
db = Database(db_path="fall_events.db")
oss_client = OSSClient(bucket_name="fall-detection-dev", region="cn-beijing")
notifier = WeChatWorkNotifier()


@app.get("/api/proxy/image")
async def proxy_image(url: str):
    """
    代理获取 OSS 图片（解决默认域名强制下载问题）
    """
    try:
        # 从 URL 中提取 object_key
        import re
        pattern = r'\.com/(.+)'
        match = re.search(pattern, url)
        if not match:
            raise HTTPException(status_code=400, detail="无效的图片URL")

        object_key = match.group(1)

        # 使用 OSS SDK 获取图片
        result = oss_client.bucket.get_object(object_key)
        img_data = result.read()

        # ✅ 使用 StreamingResponse 返回图片
        return StreamingResponse(
            iter([img_data]),  # 将 bytes 包装成迭代器
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Content-Disposition": "inline"
            }
        )

    except Exception as e:
        logger.error(f"图片代理失败: {e}")
        raise HTTPException(status_code=404, detail=f"图片获取失败: {str(e)}")

@app.post("/fall-events")
async def receive_fall_event(event: FallEvent):
    """
    接收跌倒事件，处理并存储
    """
    try:
        logger.info(f"📨 收到事件: {event.event_type} from {event.source} at {event.timestamp}")
        logger.debug(f"元数据: {event.metadata}")

        # 2. 解码图片
        img_data = base64.b64decode(event.image_base64)

        # 3. 生成文件名并上传到OSS
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

        # 使用OSS上传
        upload_result = oss_client.upload_image(event.image_base64, prefix="fall-events")

        image_url = None
        image_key = None

        if upload_result["success"]:
            image_url = upload_result["image_url"]
            image_key = upload_result["object_key"]
            logger.info(f"✅ 图片上传成功: {image_url}")
        else:
            logger.warning(f"⚠️ 图片上传失败: {upload_result['error']}")
            # 如果OSS上传失败，保存到本地作为备选
            local_path = f"fallback_images/fall_{timestamp_str}.jpg"
            os.makedirs("fallback_images", exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(img_data)
            image_url = f"file://{os.path.abspath(local_path)}"
            image_key = local_path
            logger.info(f"💾 图片已保存到本地: {image_url}")

        # 4. 准备插入数据库的数据
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

        # 5. 插入数据库
        event_id = db.insert_event(event_data)
        logger.info(f"💾 事件已存储到数据库, ID: {event_id}")

        # 6. 发送企业微信通知
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


@app.get("/events/statistics")
async def get_statistics():
    """获取事件统计信息"""
    try:
        stats = db.get_statistics()
        logger.debug(f"统计信息查询成功: {stats}")
        return stats
    except Exception as e:
        logger.error(f"查询统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询统计信息失败")


@app.get("/events")
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


@app.get("/events/{event_id}")
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


@app.patch("/events/{event_id}/status")
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


@app.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        stats = db.get_statistics()
        db_status = "ok"
        logger.debug("健康检查通过")
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.warning(f"健康检查数据库异常: {str(e)}")

    return {
        "status": "ok",
        "service": "fall-event-receiver",
        "database": db_status,
        "wechat_notification": "enabled" if notifier else "disabled"
    }


# ===== 启动服务 =====
if __name__ == "__main__":
    os.makedirs("fallback_images", exist_ok=True)

    logger.info("=" * 60)
    logger.info("🚀 跌倒检测事件接收服务启动")
    logger.info("=" * 60)
    logger.info(f"📦 OSS Bucket: fall-detection-dev")
    logger.info(f"🌍 OSS Region: cn-beijing")
    logger.info(f"📱 微信通知: {'已启用' if notifier else '未启用'}")
    logger.info(f"💾 数据库: fall_events.db")
    logger.info("=" * 60)
    logger.info("🌐 服务地址: http://localhost:8080")
    logger.info("📚 API文档: http://localhost:8080/docs")
    logger.info("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8080)