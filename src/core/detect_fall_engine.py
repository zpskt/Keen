# detect_fall_engine.py
import base64
from datetime import datetime

import cv2
import numpy as np
import requests
from ultralytics import YOLO

from face_utils import FaceRecognizer
from logger_utils import get_logger
from person_manager import PersonManager
from person_matcher import PersonMatcher

# ===== 配置 =====
MODEL_PATH = "models/yolo26n-pose.pt"
FACE_MODEL_PATH = "models/yolo26n-face.pt"  # 人脸检测模型
FASTAPI_URL = "http://127.0.0.1:8080/fall-events"
EVENT_COOLDOWN = 10  # 秒
ANGLE_THRESHOLD = 50
CONF_THRESHOLD = 0.5
FALL_FRAME_THRESHOLD = 0  # 连续跌倒帧数阈值，假设300fps，约10秒；0表示立即触发

# ===== 全局变量（状态管理） =====
last_event_time = 0
model = None  # 延迟加载
last_event_time = 0
model = None

# ===== 人员匹配相关全局变量 =====
# 必须在这里定义，在所有函数之前
person_matcher = None   # 让 PyCharm 看到这个
face_recognizer = None  # 让 PyCharm 看到这个

person_status = {}  # 新增：存储每个人状态 {track_id: {'fall_frames': 0, 'alerted': False}}

# ===== 人员匹配缓存（避免每帧都做人脸识别，提高性能） =====
person_cache = {}  # {track_id: person_info}
person_cache_frames = {}  # {track_id: 缓存帧数}
CACHE_EXPIRE_FRAMES = 30  # 缓存30帧后重新识别

# ===== 关键点索引 =====
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12

# ===== 初始化日志 =====
logger = get_logger('detect_fall_and_push')


# ===== 初始化人员匹配器 =====
def init_person_matcher():
    """延迟初始化人员匹配器"""
    global person_matcher, face_recognizer  # 声明全局变量

    if person_matcher is None:
        try:
            # 初始化人脸识别器
            face_recognizer = FaceRecognizer(
                face_model_path=FACE_MODEL_PATH,
                encoding_file="data/face_encodings.pkl"
            )
            logger.info("✅ 人脸识别器初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ 人脸识别器初始化失败: {e}")
            face_recognizer = None

        # 初始化人员管理器
        person_manager = PersonManager()

        # 初始化人员匹配器
        person_matcher = PersonMatcher(person_manager, face_recognizer)
        logger.info("✅ 人员匹配器初始化完成")

    return person_matcher


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


# ===== 事件推送（带人员信息） =====
def send_fall_event(annotated_frame, track_id, person_info=None):
    """
    推送跌倒事件，支持人员信息
    :param annotated_frame: 标注后的帧
    :param track_id: 追踪ID
    :param person_info: 人员匹配结果
    """
    # todo 未来需要加上track_id使用
    _, img_encoded = cv2.imencode('.jpg', annotated_frame)
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')
    payload = {
        'timestamp': datetime.now().isoformat(),
        "event_type": "fall",
        "source": "camera-01",
        "image_base64": img_base64,
        "confidence": 1,
        "location": "unknown",
        "metadata": {
            "track_id": track_id,
            "width": annotated_frame.shape[1],
            "height": annotated_frame.shape[0]
        }
    }
    # ===== 添加人员信息 =====
    if person_info and person_info.get('person_id'):
        payload['metadata']['person_id'] = person_info['person_id']
        payload['metadata']['person_name'] = person_info.get('person_name', '未知')
        payload['metadata']['person_confidence'] = person_info.get('confidence', 0.0)
        payload['metadata']['match_method'] = person_info.get('match_method', 'none')

        # 补充人员详细信息
        person = person_info.get('person_info', {})
        if person:
            payload['metadata']['room_number'] = person.get('room_number')
            payload['metadata']['guardian_name'] = person.get('guardian_name')
            payload['metadata']['guardian_phone'] = person.get('guardian_phone')

    try:
        response = requests.post(FASTAPI_URL, json=payload, timeout=5)
        response.raise_for_status()
        person_str = f" (人员: {person_info.get('person_name', '未知')})" if person_info and person_info.get(
            'person_id') else ""
        logger.info(f"✅ 事件推送成功, track_id={track_id}{person_str}")
    except Exception as e:
        logger.error(f"❌ 事件推送失败: {e}")


# ===== 核心函数：处理单帧 =====
def process_frame(frame):
    """
    处理一帧图像（摄像头、视频或图片），执行跌倒检测并推送事件
    :param frame: 输入帧 (numpy array, BGR格式)
    :return: (annotated_frame, status) 其中 status 为 'fall' 或 'normal'
    """
    global last_event_time, model, person_status, person_cache, person_cache_frames

    # 初始化人员匹配器
    matcher = init_person_matcher()

    # 延迟加载模型（首次调用时加载）
    if model is None:
        logger.info("⏳ 正在加载 YOLO 模型...")
        model = YOLO(MODEL_PATH)
        logger.info("✅ 模型加载完成")

    # 运行推理
    # ===== 1. 使用 track 模式进行追踪 =====
    results = model.track(frame, conf=CONF_THRESHOLD, persist=True,
                          classes=[0], verbose=False)  # classes=[0] 只检测人    annotated_frame = frame.copy()  # 默认返回原帧
    status = "normal"
    matched_person = None
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

        # 获取检测框
        bbox = None
        if i < len(boxes):
            box = boxes[i]
            bbox = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))

        # ===== 每帧都进行人员匹配（使用缓存提高性能） =====
        person_info = None

        # 检查缓存
        if track_id in person_cache and person_cache_frames.get(track_id, 0) < CACHE_EXPIRE_FRAMES:
            person_info = person_cache[track_id]
            person_cache_frames[track_id] = person_cache_frames.get(track_id, 0) + 1
        else:
            # 缓存过期或不存在，重新识别
            if matcher and bbox is not None:
                try:
                    camera_id = "camera-01"
                    metadata = {"camera_id": camera_id}

                    person_info = matcher.match_person(
                        frame=frame,
                        camera_id=camera_id,
                        track_id=track_id,
                        bbox=bbox,
                        metadata=metadata
                    )

                    # 更新缓存
                    if person_info and person_info.get('person_id'):
                        person_cache[track_id] = person_info
                        person_cache_frames[track_id] = 0
                        logger.debug(f"👤 识别到人员: {person_info.get('person_name')}")
                except Exception as e:
                    logger.error(f"人员匹配失败: {e}")
                    person_info = None

        # ===== 绘制人员名称（始终显示） =====
        if bbox is not None:
            x1, y1, x2, y2 = bbox

            # 显示人员名称
            if person_info and person_info.get('person_id'):
                name = person_info.get('person_name', '未知')
                confidence = person_info.get('confidence', 0.0)
                method = person_info.get('match_method', '')

                # 在检测框上方显示名称
                label = f"{name} ({confidence:.2f})"
                cv2.putText(annotated_frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                # 未识别到人员
                cv2.putText(annotated_frame, f"Person {track_id} (未知)", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # 4.2 判断姿态
        if is_falling(kpts_np, angle_threshold=ANGLE_THRESHOLD):
            person_status[track_id]['fall_frames'] += 1
            # 如果超过阈值且未报警，触发事件
            if person_status[track_id]['fall_frames'] > FALL_FRAME_THRESHOLD and not person_status[track_id][
                'alerted']:
                logger.info(f"⚠️ 检测到人员 {track_id} 持续跌倒超过 {FALL_FRAME_THRESHOLD} 帧！")



                # 绘制
                annotated_frame = results[0].plot()  # 绘制所有检测框和关键点
                cv2.putText(annotated_frame, f"FALL: Person {track_id}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # 如果已识别到人员，在跌倒标注中显示姓名
                if person_info and person_info.get('person_id'):
                    cv2.putText(annotated_frame, f"Person: {person_info.get('person_name')}", (10, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # 推送事件
                send_fall_event(annotated_frame, track_id)

                person_status[track_id]['alerted'] = True
                status = "fall"
                matched_person = person_info

        else:
            # 如果恢复正常姿态，重置该人的跌倒状态
            if person_status[track_id]['fall_frames'] > 0:
                logger.info(f"人员 {track_id} 已恢复正常姿态")
            person_status[track_id] = {'fall_frames': 0, 'alerted': False}

    return annotated_frame, status
