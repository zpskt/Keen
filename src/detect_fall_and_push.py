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

# ===== 全局状态管理 =====
last_event_time = 0
model = None
person_status = {}  # 新增：存储每个人状态 {track_id: {'fall_frames': 0, 'alerted': False}}
FALL_FRAME_THRESHOLD = 300  # 新增：连续跌倒帧数阈值，假设300fps，约10秒

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
    # ===== 1. 使用 track 模式进行追踪 =====
    results = model.track(frame, conf=CONF_THRESHOLD, persist=True, classes=[0])  # classes=[0] 只检测人    annotated_frame = frame.copy()  # 默认返回原帧
    status = "normal"

    annotated_frame = results[0].plot()
    # ===== 2. 检查是否检测到任何结果 =====
    if results[0].boxes is None or results[0].boxes.id is None:
        return annotated_frame, status

    # ===== 3. 提取检测框和追踪ID =====
    boxes = results[0].boxes.xyxy.cpu().numpy().astype(int) if results[0].boxes.xyxy is not None else []
    track_ids = results[0].boxes.id.cpu().numpy().astype(int) if results[0].boxes.id is not None else []

    # ===== 4. 遍历每个人 =====
    for i, track_id in enumerate(track_ids):
        if track_id not in person_status:
            person_status[track_id] = {'fall_frames': 0, 'alerted': False}

        # 4.1 提取该人的关键点 (如果存在)
        if results[0].keypoints is not None and len(results[0].keypoints.data) > i:
            kpts_np = results[0].keypoints.data[i].cpu().numpy()
        else:
            continue

        # 4.2 判断姿态
        if is_falling(kpts_np, angle_threshold=ANGLE_THRESHOLD):
            person_status[track_id]['fall_frames'] += 1
            # 如果超过阈值且未报警，触发事件
            if person_status[track_id]['fall_frames'] > FALL_FRAME_THRESHOLD and not person_status[track_id][
                'alerted']:
                print(f"⚠️ 检测到人员 {track_id} 持续跌倒超过 {FALL_FRAME_THRESHOLD} 帧！")
                # 绘制并推送事件
                annotated_frame = results[0].plot()  # 绘制所有检测框和关键点
                cv2.putText(annotated_frame, f"FALL: Person {track_id}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                send_fall_event(annotated_frame, track_id)  # 你可以扩展 send_fall_event 接收 track_id
                person_status[track_id]['alerted'] = True  # 防止重复报警
                status = "fall"
        else:
            annotated_frame = results[0].plot()
            # 如果恢复正常姿态，重置该人的跌倒状态
            if person_status[track_id]['fall_frames'] > 0:
                print(f"人员 {track_id} 已恢复正常姿态")
            person_status[track_id] = {'fall_frames': 0, 'alerted': False}
    return annotated_frame, status