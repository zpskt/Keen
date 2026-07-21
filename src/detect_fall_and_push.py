# detect_fall_engine.py
import cv2
import numpy as np
import requests
import json
import base64
from datetime import datetime
import time
from ultralytics import YOLO

# ===== 配置 =====
MODEL_PATH = "models/yolo26n-pose.pt"
FASTAPI_URL = "http://127.0.0.1:8080/fall-events"
EVENT_COOLDOWN = 10  # 秒
ANGLE_THRESHOLD = 50
CONF_THRESHOLD = 0.5

# ===== 全局变量（状态管理） =====
last_event_time = 0
model = None  # 延迟加载

# ===== 关键点索引 =====
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12


# ===== 姿态判断 =====
def is_falling(keypoints_np, angle_threshold=ANGLE_THRESHOLD, conf_threshold=CONF_THRESHOLD):
    if keypoints_np.shape[1] == 3:
        if keypoints_np[LEFT_SHOULDER][2] < conf_threshold or keypoints_np[RIGHT_HIP][2] < conf_threshold:
            return False
    pts = keypoints_np[:, :2] if keypoints_np.shape[1] >= 2 else keypoints_np
    shoulder_center = (pts[LEFT_SHOULDER] + pts[RIGHT_SHOULDER]) / 2
    hip_center = (pts[LEFT_HIP] + pts[RIGHT_HIP]) / 2
    torso_vec = shoulder_center - hip_center
    vertical_vec = np.array([0, -1])
    if np.linalg.norm(torso_vec) == 0:
        return False
    cos_angle = np.dot(torso_vec, vertical_vec) / (np.linalg.norm(torso_vec) * np.linalg.norm(vertical_vec))
    angle_deg = np.arccos(np.clip(cos_angle, -1.0, 1.0)) * 180 / np.pi
    return angle_deg > angle_threshold


# ===== 事件推送 =====
def send_fall_event(annotated_frame):
    _, img_encoded = cv2.imencode('.jpg', annotated_frame)
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "fall",
        "source": "camera-01",
        "image_base64": img_base64,
        "metadata": {"width": annotated_frame.shape[1], "height": annotated_frame.shape[0]}
    }
    try:
        response = requests.post(FASTAPI_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"✅ 事件推送成功")
    except Exception as e:
        print(f"❌ 事件推送失败: {e}")


# ===== 核心函数：处理单帧 =====
def process_frame(frame):
    """
    处理一帧图像（摄像头、视频或图片），执行跌倒检测并推送事件
    :param frame: 输入帧 (numpy array, BGR格式)
    :return: (annotated_frame, status) 其中 status 为 'fall' 或 'normal'
    """
    global last_event_time, model

    # 延迟加载模型（首次调用时加载）
    if model is None:
        print("⏳ 正在加载 YOLO 模型...")
        model = YOLO(MODEL_PATH)
        print("✅ 模型加载完成")

    # 运行推理
    results = model(frame, conf=CONF_THRESHOLD)
    annotated_frame = frame.copy()  # 默认返回原帧
    status = "normal"

    for result in results:
        # ===== 关键修改：增加安全检查 =====
        # 1. 检查 result.keypoints 是否存在
        if result.keypoints is None:
            continue

        # 2. 检查 keypoints.data 是否非空（是否有检测到的人）
        if result.keypoints.data is None or len(result.keypoints.data) == 0:
            status = 'not detect person'
            continue

        # 取第一个人的关键点
        kpts_np = result.keypoints.data[0].cpu().numpy()
        # 绘制检测结果
        annotated_frame = result.plot()
        if is_falling(kpts_np, angle_threshold=ANGLE_THRESHOLD):
            cv2.putText(annotated_frame, "FALL DETECTED!", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            status = "fall"

            # 推送事件（带冷却）
            current_time = time.time()
            if current_time - last_event_time > EVENT_COOLDOWN:
                print("⚠️ 跌倒！推送事件...")
                send_fall_event(annotated_frame)
                last_event_time = current_time
            break  # 检测到跌倒后，不再处理后续结果

    return annotated_frame, status