# fall_event_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import base64
import uvicorn
import os


# ===== 定义请求体模型 =====
class FallEvent(BaseModel):
    timestamp: str
    event_type: str
    source: str
    image_base64: str
    metadata: dict


# ===== 创建FastAPI应用 =====
app = FastAPI(title="跌倒事件接收服务", description="接收跌倒检测事件并触发后续动作", version="1.0")

# ===== 模拟存储：实际可使用数据库 =====
event_storage = []


@app.post("/fall-events")
async def receive_fall_event(event: FallEvent):
    """
    接收跌倒事件，处理并存储
    """
    try:
        # 1. 打印日志
        print(f"📨 收到事件: {event.event_type} from {event.source} at {event.timestamp}")

        # 2. 可选：将base64图像保存为文件（实际使用中可上传到OSS）
        img_data = base64.b64decode(event.image_base64)
        with open(f"fall_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg", "wb") as f:
            f.write(img_data)

        # 3. 存储事件到内存列表（实际应存入数据库）
        event_dict = event.dict()
        event_dict["received_at"] = datetime.utcnow().isoformat() + "Z"
        event_storage.append(event_dict)

        # 4. 触发后续动作（如发送短信、App推送等）
        # send_notification(event_dict)  # 实现你的通知逻辑

        return {
            "status": "success",
            "message": "事件已接收",
            "event_id": len(event_storage)
        }

    except Exception as e:
        print(f"❌ 处理事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@app.get("/events")
async def get_events():
    """获取所有已接收的事件（用于调试和展示）"""
    return {"total": len(event_storage), "events": event_storage}


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "fall-event-receiver"}


# ===== 启动服务 =====
if __name__ == "__main__":
    # 监听所有网络接口的8080端口
    uvicorn.run(app, host="0.0.0.0", port=8080)