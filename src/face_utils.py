# src/face_utils.py
import cv2
import numpy as np
import pickle
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from ultralytics import YOLO
import logging

from logger_utils import get_logger

# ===== 初始化日志 =====
logger = get_logger('face_utils')


class FaceRecognizer:
    """
    基于 YOLO 的人脸检测与识别
    使用 YOLO-Face 检测人脸，使用特征向量匹配识别身份
    """

    def __init__(self,
                 face_model_path: str = "models/yolo26n-face.pt",
                 encoding_file: str = "data/face_encodings.pkl",
                 confidence_threshold: float = 0.7,
                 match_threshold: float = 0.7):
        """
        初始化人脸识别器
        :param face_model_path: YOLO-Face 模型路径
        :param encoding_file: 人脸特征存储文件
        :param confidence_threshold: 人脸检测置信度阈值
        :param match_threshold: 人脸匹配相似度阈值
        """
        self.face_model_path = face_model_path
        self.encoding_file = encoding_file
        self.confidence_threshold = confidence_threshold
        self.match_threshold = match_threshold

        # 延迟加载模型
        self._face_model = None

        # 已知人脸库
        self.known_encodings = []  # 人脸特征向量
        self.known_person_ids = []  # 人员ID
        self.known_names = []  # 人员姓名
        self.known_person_info = []  # 完整人员信息

        # 确保数据目录存在
        os.makedirs(os.path.dirname(encoding_file), exist_ok=True)

        self._load_encodings()

    @property
    def face_model(self):
        """延迟加载 YOLO-Face 模型"""
        if self._face_model is None:
            if not os.path.exists(self.face_model_path):
                logger.warning(f"人脸模型文件不存在: {self.face_model_path}")
                logger.info("请下载模型: https://github.com/akanametov/yolo-face/releases")
                self._face_model = None
            else:
                self._face_model = YOLO(self.face_model_path, verbose=False)
                logger.info(f"✅ YOLO-Face 模型加载完成: {self.face_model_path}")
        return self._face_model

    def _load_encodings(self):
        """加载已知人脸特征"""
        if os.path.exists(self.encoding_file):
            try:
                with open(self.encoding_file, 'rb') as f:
                    data = pickle.load(f)
                    self.known_encodings = data.get('encodings', [])
                    self.known_person_ids = data.get('person_ids', [])
                    self.known_names = data.get('names', [])
                    self.known_person_info = data.get('person_info', [])
                logger.info(f"✅ 加载了 {len(self.known_encodings)} 个人脸特征")
            except Exception as e:
                logger.warning(f"加载人脸特征失败: {e}")

    def save_encodings(self):
        """保存人脸特征"""
        data = {
            'encodings': self.known_encodings,
            'person_ids': self.known_person_ids,
            'names': self.known_names,
            'person_info': self.known_person_info,
            'updated_at': datetime.now().isoformat()
        }
        with open(self.encoding_file, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"💾 保存了 {len(self.known_encodings)} 个人脸特征")

    def _extract_face_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """
        提取人脸特征向量（不使用 HOG，改用更稳定的方法）
        """
        try:
            # 统一尺寸
            face_resized = cv2.resize(face_img, (64, 64))

            # 转为灰度图
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)

            # 方法1：使用 LBP 特征（局部二值模式）
            import numpy as np
            from skimage.feature import local_binary_pattern

            # 计算 LBP 特征
            radius = 1
            n_points = 8 * radius
            lbp = local_binary_pattern(gray, n_points, radius, method='uniform')

            # 提取 LBP 直方图作为特征
            hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, n_points + 3), range=(0, n_points + 2))
            hist = hist.astype(np.float32)
            hist = hist / (hist.sum() + 1e-7)  # 归一化

            return hist

        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            return None


    def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        检测图像中的所有人脸
        :param image: 输入图像
        :return: 人脸检测结果列表
        """
        if self.face_model is None:
            return []

        try:
            results = self.face_model(image, conf=self.confidence_threshold, verbose=False)

            faces = []
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                confidences = results[0].boxes.conf.cpu().numpy()

                for i, (box, conf) in enumerate(zip(boxes, confidences)):
                    x1, y1, x2, y2 = box
                    # 确保坐标在图像范围内
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)

                    # 提取人脸区域
                    face_roi = image[y1:y2, x1:x2]

                    faces.append({
                        'bbox': (x1, y1, x2, y2),
                        'confidence': float(conf),
                        'face_image': face_roi,
                        'track_id': i
                    })

            return faces

        except Exception as e:
            logger.error(f"人脸检测失败: {e}")
            return []

    def recognize_face(self, face_img: np.ndarray) -> Dict[str, Any]:
        """
        识别单张人脸
        :param face_img: 人脸图像
        :return: 识别结果
        """
        if len(self.known_encodings) == 0:
            return {
                'person_id': None,
                'name': '未注册',
                'confidence': 0.0,
                'person_info': None
            }

        # 提取特征
        embedding = self._extract_face_embedding(face_img)
        if embedding is None:
            return {
                'person_id': None,
                'name': '未知',
                'confidence': 0.0,
                'person_info': None
            }

        # 计算相似度（余弦相似度）
        similarities = []
        for known_emb in self.known_encodings:
            sim = np.dot(embedding, known_emb) / (np.linalg.norm(embedding) * np.linalg.norm(known_emb) + 1e-8)
            similarities.append(sim)

        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]

        if best_similarity >= self.match_threshold:
            return {
                'person_id': self.known_person_ids[best_idx],
                'name': self.known_names[best_idx],
                'confidence': float(best_similarity),
                'person_info': self.known_person_info[best_idx] if best_idx < len(self.known_person_info) else None
            }
        else:
            return {
                'person_id': None,
                'name': '未知人员',
                'confidence': float(best_similarity),
                'person_info': None
            }

    def check_face_exists(self, face_img: np.ndarray, threshold: float = 0.6) -> Optional[Dict[str, Any]]:
        """
        检查人脸是否已注册
        :param face_img: 人脸图像
        :param threshold: 相似度阈值
        :return: 如果存在返回已有人员信息，否则返回 None
        """
        if len(self.known_encodings) == 0:
            return None

        embedding = self._extract_face_embedding(face_img)
        if embedding is None:
            return None

        # 计算与所有已知人脸的相似度
        similarities = []
        for known_emb in self.known_encodings:
            sim = np.dot(embedding, known_emb) / (np.linalg.norm(embedding) * np.linalg.norm(known_emb) + 1e-8)
            similarities.append(sim)

        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]

        if best_similarity >= threshold:
            return {
                'person_id': self.known_person_ids[best_idx],
                'name': self.known_names[best_idx],
                'confidence': float(best_similarity),
                'person_info': self.known_person_info[best_idx] if best_idx < len(self.known_person_info) else {}
            }

        return None

    def register_face_with_check(self, image: np.ndarray, person_id: int, name: str,
                                 person_info: dict = None,
                                 duplicate_threshold: float = 0.6) -> Dict[str, Any]:
        """
        注册人脸（带重复检查）
        :param image: 包含人脸的图像
        :param person_id: 人员ID
        :param name: 人员姓名
        :param person_info: 额外人员信息
        :param duplicate_threshold: 重复检测阈值
        :return: 注册结果
        """
        try:
            # 检测人脸
            faces = self.detect_faces(image)
            if len(faces) == 0:
                return {'success': False, 'message': '未检测到人脸'}

            face_img = faces[0]['face_image']

            # 检查是否已存在
            existing = self.check_face_exists(face_img, duplicate_threshold)

            if existing:
                existing_id = existing['person_id']
                existing_name = existing['name']

                # 如果是同一个 person_id，更新信息
                if existing_id == person_id:
                    # 更新特征（用新图片更新）
                    self._update_face_encoding(person_id, face_img, name, person_info)
                    return {
                        'success': True,
                        'message': f'已更新 {name} 的人脸特征',
                        'existing': True,
                        'person_id': person_id
                    }
                else:
                    # 不同 ID 检测到同一张脸 → 提示合并
                    return {
                        'success': False,
                        'message': f'检测到与 "{existing_name}" (ID: {existing_id}) 相似的人脸，是否合并？',
                        'existing_person': existing,
                        'conflict': True
                    }

            # 没有重复，正常注册
            embedding = self._extract_face_embedding(face_img)
            if embedding is None:
                return {'success': False, 'message': '特征提取失败'}

            # 如果该 person_id 已存在，更新
            if person_id in self.known_person_ids:
                idx = self.known_person_ids.index(person_id)
                self.known_encodings[idx] = embedding
                self.known_names[idx] = name
                self.known_person_info[idx] = person_info or {}
            else:
                self.known_encodings.append(embedding)
                self.known_person_ids.append(person_id)
                self.known_names.append(name)
                self.known_person_info.append(person_info or {})

            self.save_encodings()
            logger.info(f"✅ 注册人脸成功: {name} (person_id={person_id})")
            return {'success': True, 'message': f'注册成功: {name}', 'person_id': person_id}

        except Exception as e:
            logger.error(f"注册人脸失败: {e}")
            return {'success': False, 'message': str(e)}

    def _update_face_encoding(self, person_id: int, face_img: np.ndarray,
                              name: str, person_info: dict):
        """更新已有人员的人脸特征"""
        embedding = self._extract_face_embedding(face_img)
        if embedding is None:
            return

        if person_id in self.known_person_ids:
            idx = self.known_person_ids.index(person_id)
            # 特征融合：加权平均（保留旧特征的部分信息）
            old_embedding = self.known_encodings[idx]
            # 0.3 旧特征 + 0.7 新特征（让新特征影响更大）
            merged_embedding = 0.3 * old_embedding + 0.7 * embedding
            merged_embedding = merged_embedding / (np.linalg.norm(merged_embedding) + 1e-8)

            self.known_encodings[idx] = merged_embedding
            self.known_names[idx] = name
            self.known_person_info[idx] = person_info or {}
            self.save_encodings()
            logger.info(f"🔄 更新人脸特征: {name} (person_id={person_id})")

    def register_face_interactive(self, image: np.ndarray) -> Dict[str, Any]:
        """
        交互式注册（处理冲突）
        """
        # 检测人脸
        faces = self.detect_faces(image)
        if len(faces) == 0:
            return {'success': False, 'message': '未检测到人脸'}

        face_img = faces[0]['face_image']

        # 检查是否已存在
        existing = self.check_face_exists(face_img)

        if existing:
            print(f"\n⚠️ 检测到已有人员: {existing['name']} (ID: {existing['person_id']})")
            print(f"   相似度: {existing['confidence']:.2f}")
            print("\n选项:")
            print("  1. 更新此人脸特征")
            print("  2. 注册为新人员（不同的人）")
            print("  3. 取消注册")

            choice = input("请选择 (1/2/3): ").strip()

            if choice == '1':
                person_id = existing['person_id']
                name = input("请输入姓名（直接回车保持原名）: ").strip()
                if not name:
                    name = existing['name']
                person_info = {
                    'room': input("请输入房间号: ").strip(),
                    'phone': input("请输入电话: ").strip()
                }
                self._update_face_encoding(person_id, face_img, name, person_info)
                return {'success': True, 'message': f'已更新: {name}'}

            elif choice == '2':
                # 注册为新人员
                person_id = int(input("请输入新人员ID: "))
                name = input("请输入姓名: ")
                person_info = {
                    'room': input("请输入房间号: ").strip(),
                    'phone': input("请输入电话: ").strip()
                }
                return self.register_face_with_check(image, person_id, name, person_info)

            else:
                return {'success': False, 'message': '已取消注册'}

        # 没有重复，正常注册
        person_id = int(input("请输入人员ID: "))
        name = input("请输入姓名: ")
        person_info = {
            'room': input("请输入房间号: ").strip(),
            'phone': input("请输入电话: ").strip()
        }
        return self.register_face_with_check(image, person_id, name, person_info)
    def register_face(self, image: np.ndarray, person_id: int, name: str,
                      person_info: dict = None) -> bool:
        """
        注册人脸
        :param image: 包含人脸的图像
        :param person_id: 人员ID
        :param name: 人员姓名
        :param person_info: 额外人员信息
        """
        try:
            # 检测人脸
            faces = self.detect_faces(image)

            if len(faces) == 0:
                logger.warning("未检测到人脸")
                return False

            # 使用检测到的第一个人脸
            face_img = faces[0]['face_image']

            # 提取特征
            embedding = self._extract_face_embedding(face_img)
            if embedding is None:
                logger.warning("特征提取失败")
                return False
            # todo 如果同一个脸注册不同的id怎么处理？
            # 如果该人已有特征，先移除旧的
            if person_id in self.known_person_ids:
                idx = self.known_person_ids.index(person_id)
                del self.known_encodings[idx]
                del self.known_person_ids[idx]
                del self.known_names[idx]
                if idx < len(self.known_person_info):
                    del self.known_person_info[idx]

            # 添加新特征
            self.known_encodings.append(embedding)
            self.known_person_ids.append(person_id)
            self.known_names.append(name)
            self.known_person_info.append(person_info or {})

            self.save_encodings()
            logger.info(f"✅ 注册人脸成功: {name} (person_id={person_id})")
            return True

        except Exception as e:
            logger.error(f"注册人脸失败: {e}")
            return False

    def recognize_from_image(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        从图像中检测并识别所有人脸
        :param image: 输入图像
        :return: 识别结果列表
        """
        # 检测人脸
        faces = self.detect_faces(image)

        results = []
        for face_data in faces:
            # 识别
            recognition = self.recognize_face(face_data['face_image'])
            results.append({
                **face_data,
                **recognition
            })

        return results

    def recognize_person_in_frame(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """
        在指定区域内识别人脸（用于跌倒检测场景）
        :param frame: 视频帧
        :param bbox: 人体检测框 (x1, y1, x2, y2)
        :return: 识别结果
        """
        x1, y1, x2, y2 = bbox

        # 提取人体上半部分（头部区域）
        head_y2 = y1 + int((y2 - y1) * 0.4)  # 取上半部分
        head_roi = frame[y1:head_y2, x1:x2]

        if head_roi.size == 0:
            return {'person_id': None, 'name': '未知', 'confidence': 0.0, 'person_info': None}

        # 从头部区域检测人脸
        faces = self.detect_faces(head_roi)

        if len(faces) == 0:
            return {'person_id': None, 'name': '未知', 'confidence': 0.0, 'person_info': None}

        # 使用第一个检测到的人脸
        face_img = faces[0]['face_image']
        return self.recognize_face(face_img)

    def get_person_info(self, person_id: int) -> Optional[Dict[str, Any]]:
        """根据人员ID获取完整信息"""
        if person_id in self.known_person_ids:
            idx = self.known_person_ids.index(person_id)
            return {
                'person_id': person_id,
                'name': self.known_names[idx],
                'info': self.known_person_info[idx] if idx < len(self.known_person_info) else {}
            }
        return None


# ===== 快速测试 =====
if __name__ == '__main__':
    import time

    # 初始化
    recognizer = FaceRecognizer(face_model_path="models/yolo26n-face.pt")

    # 测试摄像头注册和识别
    cap = cv2.VideoCapture(0)

    print("=" * 50)
    print("人脸识别测试")
    print("按 'r' - 注册人脸")
    print("按 'q' - 退出")
    print("=" * 50)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 检测人脸
        faces = recognizer.detect_faces(frame)

        # 绘制结果
        for face in faces:
            x1, y1, x2, y2 = face['bbox']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 识别
            result = recognizer.recognize_face(face['face_image'])
            name = result['name'] if result['name'] else '未知'
            conf = result['confidence']

            cv2.putText(frame, f"{name} ({conf:.2f})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow('Face Recognition', frame)
        key = cv2.waitKey(1)

        if key == ord('r'):
            person_id = int(input("请输入人员ID: "))
            name = input("请输入人员姓名: ")
            if recognizer.register_face(frame, person_id, name):
                print(f"✅ 注册成功: {name}")
            else:
                print("❌ 注册失败")

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()