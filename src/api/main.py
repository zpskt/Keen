# main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
import os
import re

from src.util.logger_utils import get_logger
from src.api.routes.person_api import router as person_router
from src.api.routes.report_api import router as report_router
from src.api.routes.events import router as events_router
from src.util.oss_utils import OSSClient
from src.database.fall_events_manager import Database

# ===== 初始化日志 =====
logger = get_logger('fall_event_server')

# ===== 创建FastAPI应用 =====
app = FastAPI(title="跌倒事件接收服务", description="接收跌倒检测事件并触发后续动作", version="1.0")

# ===== 注册路由 =====
app.include_router(events_router)  # 事件接口: /fall-events, /events/*
app.include_router(person_router)  # 人员管理: /api/persons
app.include_router(report_router)  # 数据报表: /api/reports

# ===== 图片代理（单独保留在主入口） =====
oss_client = OSSClient(bucket_name="fall-detection-dev", region="cn-beijing")


@app.get("/api/proxy/image")
async def proxy_image(url: str):
    """代理获取 OSS 图片"""
    try:
        pattern = r'\.com/(.+)'
        match = re.search(pattern, url)
        if not match:
            raise HTTPException(status_code=400, detail="无效的图片URL")
        object_key = match.group(1)
        result = oss_client.bucket.get_object(object_key)
        img_data = result.read()
        return StreamingResponse(
            iter([img_data]),
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Content-Disposition": "inline"
            }
        )
    except Exception as e:
        logger.error(f"图片代理失败: {e}")
        raise HTTPException(status_code=404, detail=f"图片获取失败: {str(e)}")


# ===== 健康检查 =====
@app.get("/health")
async def health_check():
    """健康检查接口"""
    db = Database(db_path="fall_events.db")
    try:
        stats = db.get_statistics()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.warning(f"健康检查数据库异常: {str(e)}")
    return {
        "status": "ok",
        "service": "fall-event-receiver",
        "database": db_status
    }


# ===== 启动服务 =====
if __name__ == "__main__":
    os.makedirs("fallback_images", exist_ok=True)

    logger.info("=" * 60)
    logger.info("🚀 跌倒检测事件接收服务启动")
    logger.info("=" * 60)
    logger.info("🌐 服务地址: http://localhost:8080")
    logger.info("📚 API文档: http://localhost:8080/docs")
    logger.info("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8080)