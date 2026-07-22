# src/db_utils.py
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class Database:
    """SQLite 数据库操作封装"""

    def __init__(self, db_path: str = "fall_events.db"):
        """
        初始化数据库
        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_database()

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 创建跌倒事件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fall_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type VARCHAR(50) NOT NULL,
                    source VARCHAR(100) NOT NULL,
                    event_time DATETIME NOT NULL,
                    received_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    confidence VARCHAR(100) NOT NULL,
                    -- 图片信息
                    image_url VARCHAR(500),
                    image_key VARCHAR(200),
                    image_bucket VARCHAR(100),
                    image_region VARCHAR(50),

                    -- 元数据（JSON格式存储）
                    metadata TEXT,

                    -- 处理状态
                    status INTEGER DEFAULT 0,
                    processed_at DATETIME,
                    notification_sent INTEGER DEFAULT 0,
                    notification_time DATETIME,

                    -- 备注
                    remark VARCHAR(500),

                    -- 审计字段
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_time 
                ON fall_events(event_time DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type 
                ON fall_events(event_type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON fall_events(status)
            """)

            print("✅ 数据库初始化完成")

    def insert_event(self, event_data: Dict[str, Any]) -> int:
        """
        插入跌倒事件
        :param event_data: 事件数据字典
        :return: 插入的记录ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 处理 metadata（转为JSON字符串）
            metadata = event_data.get('metadata')
            if metadata and isinstance(metadata, dict):
                metadata = json.dumps(metadata, ensure_ascii=False)

            cursor.execute("""
                INSERT INTO fall_events (
                    event_type, source, event_time, received_time,confidence,
                    image_url, image_key, image_bucket, image_region,
                    metadata, status, remark
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
            """, (
                event_data.get('event_type'),
                event_data.get('source'),
                event_data.get('event_time'),
                event_data.get('received_time', datetime.now().isoformat()),
                event_data.get('confidence'),
                event_data.get('image_url'),
                event_data.get('image_key'),
                event_data.get('image_bucket'),
                event_data.get('image_region'),
                metadata,
                event_data.get('status', 0),
                event_data.get('remark')
            ))

            return cursor.lastrowid

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查询事件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fall_events WHERE id = ?", (event_id,))
            row = cursor.fetchone()

            if row:
                result = dict(row)
                # 解析 metadata
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = {}
                return result
            return None

    def get_events(self, limit: int = 100, offset: int = 0,
                   event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取事件列表
        :param limit: 限制数量
        :param offset: 偏移量
        :param event_type: 过滤事件类型
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM fall_events"
            params = []

            if event_type:
                query += " WHERE event_type = ?"
                params.append(event_type)

            query += " ORDER BY event_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = {}
                results.append(result)

            return results

    def update_event_status(self, event_id: int, status: int,
                            processed_at: Optional[str] = None) -> bool:
        """
        更新事件状态
        :param event_id: 事件ID
        :param status: 状态值 (0-待处理, 1-处理中, 2-已完成, 3-失败)
        :param processed_at: 处理完成时间
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if processed_at:
                cursor.execute("""
                    UPDATE fall_events 
                    SET status = ?, processed_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, processed_at, event_id))
            else:
                cursor.execute("""
                    UPDATE fall_events 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, event_id))

            return cursor.rowcount > 0

    def mark_notification_sent(self, event_id: int) -> bool:
        """标记通知已发送"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE fall_events 
                SET notification_sent = 1, 
                    notification_time = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (event_id,))
            return cursor.rowcount > 0

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 总数统计
            cursor.execute("SELECT COUNT(*) as total FROM fall_events")
            total = cursor.fetchone()['total']

            # 按状态统计
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM fall_events 
                GROUP BY status
            """)
            status_stats = {row['status']: row['count'] for row in cursor.fetchall()}

            # 今日事件数
            cursor.execute("""
                SELECT COUNT(*) as today 
                FROM fall_events 
                WHERE DATE(event_time) = DATE('now')
            """)
            today = cursor.fetchone()['today']

            return {
                'total': total,
                'today': today,
                'pending': status_stats.get(0, 0),
                'processing': status_stats.get(1, 0),
                'completed': status_stats.get(2, 0),
                'failed': status_stats.get(3, 0)
            }