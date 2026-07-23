# src/person_manager.py
import random
import sqlite3
import json
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import cv2
import base64
from logger_utils import get_logger
import numpy as np

from oss_utils import OSSClient

logger = get_logger('person_manager')


class PersonManager:
    """人员信息管理（独立于人脸识别）"""

    def __init__(self, db_path: str = "fall_events.db", photo_dir: str = "data/photos"):
        """
        初始化人员管理器
        :param db_path: 数据库路径
        :param photo_dir: 照片存储目录
        """
        self.db_path = db_path
        self.photo_dir = photo_dir
        os.makedirs(photo_dir, exist_ok=True)
        self._init_tables()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self):
        """初始化人员表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 创建人员表（包含照片字段）
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS persons
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               name
                               VARCHAR
                           (
                               50
                           ) NOT NULL,
                               age INTEGER,
                               gender VARCHAR
                           (
                               10
                           ) DEFAULT '未知',
                               room_number VARCHAR
                           (
                               20
                           ),
                               bed_number VARCHAR
                           (
                               20
                           ),
                               floor VARCHAR
                           (
                               20
                           ),
                               building VARCHAR
                           (
                               50
                           ),
                               guardian_name VARCHAR
                           (
                               50
                           ),
                               guardian_phone VARCHAR
                           (
                               20
                           ),
                               guardian_relationship VARCHAR
                           (
                               20
                           ),
                               medical_history TEXT,
                               special_notes TEXT,
                               photo_path VARCHAR
                           (
                               200
                           ),
                               face_encoding_id INTEGER,
                               status INTEGER DEFAULT 1,
                               created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                               updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                               )
                           """)

            # 检查并添加缺失字段
            cursor.execute("PRAGMA table_info(persons)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'photo_path' not in columns:
                cursor.execute("ALTER TABLE persons ADD COLUMN photo_path VARCHAR(200)")
                logger.info("✅ 添加字段: photo_path")

            if 'face_encoding_id' not in columns:
                cursor.execute("ALTER TABLE persons ADD COLUMN face_encoding_id INTEGER")
                logger.info("✅ 添加字段: face_encoding_id")

            logger.info("✅ 人员管理表初始化完成")

    # ===== 人员 CRUD =====

    def add_person(self, person_data: Dict[str, Any], photo_image: Any = None) -> int:
        """
        添加人员
        :param person_data: 人员信息字典
        :param photo_image: 照片（numpy array 或文件路径）
        :return: 人员ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 保存照片
            photo_path = self._save_photo(photo_image, person_data.get('name', 'unknown'))
            person_data['photo_path'] = photo_path

            cursor.execute("""
                           INSERT INTO persons (name, age, gender, room_number, bed_number,
                                                floor, building, guardian_name, guardian_phone,
                                                guardian_relationship, medical_history, special_notes,
                                                photo_path, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (
                               person_data.get('name'),
                               person_data.get('age'),
                               person_data.get('gender', '未知'),
                               person_data.get('room_number'),
                               person_data.get('bed_number'),
                               person_data.get('floor'),
                               person_data.get('building'),
                               person_data.get('guardian_name'),
                               person_data.get('guardian_phone'),
                               person_data.get('guardian_relationship'),
                               person_data.get('medical_history'),
                               person_data.get('special_notes'),
                               photo_path,
                               person_data.get('status', 1)
                           ))

            person_id = cursor.lastrowid
            logger.info(f"✅ 添加人员成功: {person_data.get('name')} (ID: {person_id})")
            return person_id

    def _save_photo(self, photo_image, name: str) -> Optional[str]:
        """保存照片到本地"""
        if photo_image is None:
            return None

        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            num = random.randint(1, 10)
            filename = f"{num}_{timestamp}.jpg"
            filepath = os.path.join(self.photo_dir, filename)

            # 如果是 numpy array (cv2 图像)
            if isinstance(photo_image, np.ndarray):
                cv2.imwrite(filepath, photo_image)

            # 如果是文件路径
            elif isinstance(photo_image, str) and os.path.exists(photo_image):
                shutil.copy(photo_image, filepath)

            # 如果是 base64 字符串
            elif isinstance(photo_image, str) and photo_image.startswith('data:image'):

                img_data = base64.b64decode(photo_image.split(',')[1])
                with open(filepath, 'wb') as f:
                    f.write(img_data)

            # 1. 配置测试参数（请替换为你的实际值）
            BUCKET_NAME = "fall-detection-dev"  # 替换为你的Bucket名称
            REGION = "cn-beijing"  # 替换为你的Bucket地域

            # 2. 初始化OSS客户端
            client = OSSClient(bucket_name=BUCKET_NAME, region=REGION)

            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    image_bytes = f.read()
                    test_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    logger.info(f"✅ 已加载测试图片: {filepath}, Base64长度: {len(test_base64)}")
            else:
                logger.info(f"⚠️ 未找到测试图片 {filepath}，请准备一张图片")
                exit(1)

            # 4. 执行上传测试
            result = client.upload(test_base64, prefix="person_Avatar")

            # 5. 打印结果
            if result["success"]:
                return result['image_url']
            else:
                logger.error(f"❌ 上传失败: {result['error']}")
            return None

        except Exception as e:
            logger.error(f"保存照片失败: {e}")
            return None

    def get_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        """获取人员信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM persons WHERE id = ? AND status = 1", (person_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_persons(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取人员列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT *
                           FROM persons
                           WHERE status = 1
                           ORDER BY created_at DESC LIMIT ?
                           OFFSET ?
                           """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def update_person(self, person_id: int, person_data: Dict[str, Any],
                      photo_image: Any = None) -> bool:
        """更新人员信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            values = []

            # 可更新字段
            updateable_fields = [
                'name', 'age', 'gender', 'room_number', 'bed_number',
                'floor', 'building', 'guardian_name', 'guardian_phone',
                'guardian_relationship', 'medical_history', 'special_notes', 'status'
            ]

            for key in updateable_fields:
                if key in person_data:
                    fields.append(f"{key} = ?")
                    values.append(person_data[key])

            # 如果有新照片，更新照片
            if photo_image is not None:
                # 获取旧照片路径并删除
                old_person = self.get_person(person_id)
                if old_person and old_person.get('photo_path'):
                    try:
                        os.remove(old_person['photo_path'])
                    except:
                        pass

                # 保存新照片
                name = person_data.get('name', 'unknown')
                photo_path = self._save_photo(photo_image, name)
                if photo_path:
                    fields.append("photo_path = ?")
                    values.append(photo_path)

            values.append(person_id)
            cursor.execute(f"""
                UPDATE persons SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            return cursor.rowcount > 0

    def delete_person(self, person_id: int) -> bool:
        """软删除人员"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE persons SET status = 0 WHERE id = ?", (person_id,))
            return cursor.rowcount > 0

    def delete_person_permanently(self, person_id: int) -> bool:
        """永久删除人员（删除照片）"""
        person = self.get_person(person_id)
        if person and person.get('photo_path'):
            try:
                os.remove(person['photo_path'])
            except:
                pass

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM persons WHERE id = ?", (person_id,))
            return cursor.rowcount > 0

    def search_persons(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索人员"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT *
                           FROM persons
                           WHERE status = 1
                             AND (name LIKE ? OR room_number LIKE ? OR guardian_name LIKE ?)
                           ORDER BY name
                           """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM persons WHERE status = 1")
            total = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as male FROM persons WHERE gender = '男' AND status = 1")
            male = cursor.fetchone()['male']

            cursor.execute("SELECT COUNT(*) as female FROM persons WHERE gender = '女' AND status = 1")
            female = cursor.fetchone()['female']

            cursor.execute("""
                           SELECT COUNT(DISTINCT room_number) as rooms
                           FROM persons
                           WHERE status = 1
                             AND room_number IS NOT NULL
                           """)
            rooms = cursor.fetchone()['rooms']

            return {
                'total': total,
                'male': male,
                'female': female,
                'rooms': rooms
            }

    def get_photo_base64(self, photo_path: str) -> Optional[str]:
        """获取照片的 Base64 编码"""
        if not photo_path or not os.path.exists(photo_path):
            return None

        try:
            with open(photo_path, 'rb') as f:
                img_data = f.read()
                return base64.b64encode(img_data).decode('utf-8')
        except Exception as e:
            logger.error(f"读取照片失败: {e}")
            return None

    def bind_person_to_camera(self, person_id: int, camera_id: str, track_id: int = None) -> bool:
        """
        将人员绑定到摄像头
        :param person_id: 人员ID
        :param camera_id: 摄像头ID
        :param track_id: 追踪ID（可选）
        :return: 是否成功
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 检查 person_camera_mapping 表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person_camera_mapping'")
            if not cursor.fetchone():
                # 如果表不存在，创建
                cursor.execute("""
                               CREATE TABLE IF NOT EXISTS person_camera_mapping
                               (
                                   id
                                   INTEGER
                                   PRIMARY
                                   KEY
                                   AUTOINCREMENT,
                                   person_id
                                   INTEGER
                                   NOT
                                   NULL,
                                   camera_id
                                   VARCHAR
                               (
                                   50
                               ) NOT NULL,
                                   track_id INTEGER,
                                   created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                   FOREIGN KEY
                               (
                                   person_id
                               ) REFERENCES persons
                               (
                                   id
                               ),
                                   UNIQUE
                               (
                                   person_id,
                                   camera_id
                               )
                                   )
                               """)
                logger.info("✅ 创建 person_camera_mapping 表")

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO person_camera_mapping (person_id, camera_id, track_id)
                    VALUES (?, ?, ?)
                """, (person_id, camera_id, track_id))
                logger.info(f"✅ 绑定成功: person_id={person_id}, camera={camera_id}")
                return True
            except Exception as e:
                logger.error(f"绑定失败: {e}")
                return False

    def find_person_by_camera(self, camera_id: str, track_id: int = None) -> Optional[Dict[str, Any]]:
        """
        根据摄像头和追踪ID查找人员
        :param camera_id: 摄像头ID
        :param track_id: 追踪ID（可选）
        :return: 人员信息
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person_camera_mapping'")
            if not cursor.fetchone():
                return None

            if track_id:
                cursor.execute("""
                               SELECT p.*
                               FROM persons p
                                        JOIN person_camera_mapping m ON p.id = m.person_id
                               WHERE m.camera_id = ?
                                 AND m.track_id = ?
                                 AND p.status = 1
                               """, (camera_id, track_id))
            else:
                cursor.execute("""
                               SELECT p.*
                               FROM persons p
                                        JOIN person_camera_mapping m ON p.id = m.person_id
                               WHERE m.camera_id = ?
                                 AND p.status = 1
                               ORDER BY m.created_at DESC LIMIT 1
                               """, (camera_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_person_by_room(self, room_number: str) -> List[Dict[str, Any]]:
        """
        根据房间号获取人员列表
        :param room_number: 房间号
        :return: 人员列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT *
                           FROM persons
                           WHERE room_number = ?
                             AND status = 1
                           ORDER BY name
                           """, (room_number,))
            return [dict(row) for row in cursor.fetchall()]

# ===== 快速测试 =====
if __name__ == '__main__':


    pm = PersonManager()

    # 创建测试照片（纯色图片）
    test_img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.putText(test_img, "Test", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # 添加测试人员
    person_id = pm.add_person({
        'name': '张建国',
        'age': 78,
        'gender': '男',
        'room_number': '301',
        'bed_number': 'A01',
        'floor': '3楼',
        'building': '2号楼',
        'guardian_name': '张小明',
        'guardian_phone': '13800138001',
        'guardian_relationship': '儿子',
        'medical_history': '高血压、糖尿病',
        'special_notes': '行动不便'
    }, test_img)
    print(f"✅ 添加人员成功，ID: {person_id}")

    # 查询人员列表
    persons = pm.get_persons()
    for p in persons:
        print(f"  {p['name']} - {p['room_number']} - 监护人: {p['guardian_name']}")