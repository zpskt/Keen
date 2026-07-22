# fall_event_server.py
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
import base64
import uvicorn
import os
from typing import Optional

from oss_utils import OSSClient
from db_utils import Database
from wechat_work_utils import WeChatWorkNotifier

# ===== 定义请求体模型 =====
class FallEvent(BaseModel):
    timestamp: str
    event_type: str
    source: str
    image_base64: str
    metadata: dict


# ===== 创建FastAPI应用 =====
app = FastAPI(title="跌倒事件接收服务", description="接收跌倒检测事件并触发后续动作", version="1.0")

# ===== 初始化数据库和OSS客户端 =====
db = Database(db_path="fall_events.db")
oss_client = OSSClient(bucket_name="fall-detection-dev", region="cn-beijing")
notifier = WeChatWorkNotifier()

@app.post("/fall-events")
async def receive_fall_event(event: FallEvent):
    """
    接收跌倒事件，处理并存储
    """
    try:
        # 1. 打印日志
        print(f"📨 收到事件: {event.event_type} from {event.source} at {event.timestamp}")

        # 2. 解码图片
        img_data = base64.b64decode(event.image_base64)

        # 3. 生成文件名并上传到OSS
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        object_key = f"fall-events/fall_{timestamp_str}.jpg"

        # 使用OSS上传
        upload_result = oss_client.upload_image(event.image_base64, prefix="fall-events")

        image_url = None
        image_key = None

        if upload_result["success"]:
            image_url = upload_result["image_url"]
            image_key = upload_result["object_key"]
            print(f"✅ 图片上传成功: {image_url}")
        else:
            print(f"⚠️ 图片上传失败: {upload_result['error']}")
            # 如果OSS上传失败，保存到本地作为备选
            local_path = f"fallback_images/fall_{timestamp_str}.jpg"
            os.makedirs("fallback_images", exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(img_data)
            image_url = f"file://{os.path.abspath(local_path)}"
            image_key = local_path

        # 4. 准备插入数据库的数据
        event_data = {
            'event_type': event.event_type,
            'source': event.source,
            'event_time': event.timestamp,
            'received_time': datetime.now().isoformat(),
            'image_url': image_url,
            'image_key': image_key,
            'image_bucket': "fall-detection-dev",
            'image_region': "cn-beijing",
            'metadata': event.metadata,
            'status': 0,  # 待处理
            'remark': f"从 {event.source} 接收"
        }

        # 5. 插入数据库
        event_id = db.insert_event(event_data)
        print(f"💾 事件已存储到数据库, ID: {event_id}")

        # 6. 触发后续动作（如发送通知）
        # 这里可以调用通知服务
        # await send_notification(event_id, event_data)

        # 测试文本消息
        result = notifier.send_text("测试消息：跌倒检测服务正常运行")
        # 5. 发送企业微信通知（包含时间、地点、图片URL）
        notification_result = notifier.send_fall_alert_notification(
            event_data=event_data,
            event_id=event_id,
            image_url=image_url
        )
        # 7. 更新状态为已完成（如果需要）
        # db.update_event_status(event_id, 2, datetime.now().isoformat())

        return {
            "status": "success",
            "message": "事件已接收并存储",
            "event_id": event_id,
            "image_url": image_url
        }

    except Exception as e:
        print(f"❌ 处理事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")
@app.get("/events/statistics")
async def get_statistics():
    """获取事件统计信息"""
    stats = db.get_statistics()
    return stats

@app.get("/events")
async def get_events(
        limit: int = Query(100, description="返回数量"),
        offset: int = Query(0, description="偏移量"),
        event_type: Optional[str] = Query(None, description="过滤事件类型")
):
    """获取所有已接收的事件"""
    events = db.get_events(limit=limit, offset=offset, event_type=event_type)
    return {
        "total": len(events),
        "limit": limit,
        "offset": offset,
        "events": events
    }


@app.get("/events/{event_id}")
async def get_event(event_id: int):
    """获取单个事件的详细信息"""
    event = db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    return event


@app.patch("/events/{event_id}/status")
async def update_event_status(event_id: int, status: int):
    """
    更新事件状态
    status: 0-待处理, 1-处理中, 2-已完成, 3-失败
    """
    if status not in [0, 1, 2, 3]:
        raise HTTPException(status_code=400, detail="无效的状态值")

    success = db.update_event_status(event_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="事件不存在")

    return {"status": "success", "message": f"事件 {event_id} 状态已更新为 {status}"}





@app.get("/health")
async def health_check():
    """健康检查接口"""
    # 检查数据库是否正常
    try:
        stats = db.get_statistics()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "service": "fall-event-receiver",
        "database": db_status
    }


# ===== 启动服务 =====
if __name__ == "__main__":
    # 创建备份目录
    os.makedirs("fallback_images", exist_ok=True)

    # 监听所有网络接口的8080端口
    uvicorn.run(app, host="0.0.0.0", port=8080)