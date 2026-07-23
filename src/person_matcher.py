# src/person_matcher.py
#人员匹配
import cv2
import numpy as np
from typing import Optional, Dict, Any, Tuple
from logger_utils import get_logger

logger = get_logger('person_matcher')


class PersonMatcher:
    """
    人员匹配器：将跌倒检测到的人与人员库匹配
    支持多种匹配方式：人脸识别、位置匹配、摄像头绑定
    """

    def __init__(self, person_manager, face_recognizer=None):
        """
        初始化人员匹配器
        :param person_manager: 人员管理器实例
        :param face_recognizer: 人脸识别器实例（可选）
        """
        self.person_manager = person_manager
        self.face_recognizer = face_recognizer

        # 摄像头 → 房间号 映射（可配置）
        self.camera_room_map = {
            'CAM-001': '301',
            'CAM-002': '302',
            'CAM-003': '303',
            'camera_001': '301',
            'camera_002': '302',
            'camera_003': '303',
        }

    def match_by_face(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[Dict[str, Any]]:
        """
        方式1：通过人脸识别匹配人员
        :param frame: 视频帧
        :param bbox: 人体检测框 (x1, y1, x2, y2)
        :return: 匹配到的人员信息
        """
        if self.face_recognizer is None:
            return None

        try:
            x1, y1, x2, y2 = bbox
            # 提取头部区域
            head_y2 = y1 + int((y2 - y1) * 0.4)
            head_roi = frame[y1:head_y2, x1:x2]

            if head_roi.size == 0:
                return None

            # 识别人脸
            result = self.face_recognizer.recognize_person_in_frame(frame, bbox)
            # todo 这里需要修改，这里result.get('person_id')其实是注册时候自己填的id，并非数据库中的主键id，但是这里直接用这个字段去数据库查了
            if result and result.get('person_id'):
                # 获取完整人员信息
                person = self.person_manager.get_person(result['person_id'])
                if person:
                    logger.info(f"✅ 人脸识别匹配成功: {person['name']} (置信度: {result['confidence']:.2f})")
                    return {
                        'person_id': person['id'],
                        'person_name': person['name'],
                        'person_info': person,
                        'match_method': 'face_recognition',
                        'confidence': result['confidence']
                    }

            return None

        except Exception as e:
            logger.error(f"人脸匹配失败: {e}")
            return None

    def match_by_camera_binding(self, camera_id: str, track_id: int = None) -> Optional[Dict[str, Any]]:
        """
        方式2：通过摄像头-人员绑定匹配
        :param camera_id: 摄像头ID
        :param track_id: 追踪ID（可选）
        :return: 匹配到的人员信息
        """
        try:
            person = self.person_manager.find_person_by_camera(camera_id, track_id)
            if person:
                logger.info(f"✅ 摄像头绑定匹配成功: {person['name']} (camera: {camera_id})")
                return {
                    'person_id': person['id'],
                    'person_name': person['name'],
                    'person_info': person,
                    'match_method': 'camera_binding',
                    'confidence': 0.8
                }
            return None

        except Exception as e:
            logger.error(f"摄像头绑定匹配失败: {e}")
            return None

    def match_by_location(self, camera_id: str, metadata: dict) -> Optional[Dict[str, Any]]:
        """
        方式3：通过位置（房间号）匹配人员
        :param camera_id: 摄像头ID
        :param metadata: 事件元数据
        :return: 匹配到的人员信息
        """
        try:
            location = metadata.get('location', '')

            # 从摄像头映射获取房间号
            room_number = self.camera_room_map.get(camera_id)

            # 如果 metadata 中有房间号，优先使用
            if not room_number and location:
                import re
                room_match = re.search(r'(\d+)', location)
                if room_match:
                    room_number = room_match.group(1)

            if not room_number:
                return None

            # 查询该房间的人员
            persons = self.person_manager.get_person_by_room(room_number)

            if len(persons) == 1:
                # 如果房间只有一个人，直接匹配
                person = persons[0]
                logger.info(f"✅ 位置匹配成功: {person['name']} (房间: {room_number})")
                return {
                    'person_id': person['id'],
                    'person_name': person['name'],
                    'person_info': person,
                    'match_method': 'location',
                    'confidence': 0.6
                }
            elif len(persons) > 1:
                # 多个人，记录日志但不自动匹配
                logger.info(f"⚠️ 房间 {room_number} 有多人: {[p['name'] for p in persons]}")
                return None

            return None

        except Exception as e:
            logger.error(f"位置匹配失败: {e}")
            return None

    def match_person(self, frame: np.ndarray, camera_id: str,
                     track_id: int, bbox: Tuple[int, int, int, int],
                     metadata: dict) -> Dict[str, Any]:
        """
        综合匹配人员（按优先级尝试多种方式）
        :param frame: 视频帧
        :param camera_id: 摄像头ID
        :param track_id: 追踪ID
        :param bbox: 人体检测框
        :param metadata: 事件元数据
        :return: 匹配结果
        """
        result = {
            'person_id': None,
            'person_name': None,
            'person_info': None,
            'match_method': 'none',
            'confidence': 0.0
        }

        # 1. 优先：人脸识别（最高置信度）
        if frame is not None and bbox is not None:
            face_result = self.match_by_face(frame, bbox)
            if face_result:
                return {**result, **face_result}

        # 2. 次优：摄像头绑定
        if camera_id:
            binding_result = self.match_by_camera_binding(camera_id, track_id)
            if binding_result:
                return {**result, **binding_result}

        # 3. 保底：位置匹配
        if camera_id and metadata:
            location_result = self.match_by_location(camera_id, metadata)
            if location_result:
                return {**result, **location_result}

        # 未匹配到
        logger.info(f"⚠️ 未匹配到人员: camera={camera_id}, track={track_id}")
        return result



# ===== 快速测试 =====
if __name__ == '__main__':
    from person_manager import PersonManager

    pm = PersonManager()
    matcher = PersonMatcher(pm)

    # 测试摄像头绑定
    pm.bind_person_to_camera(1, 'CAM-001')

    # 测试匹配
    result = matcher.match_by_camera_binding('CAM-001')
    print(f"匹配结果: {result}")