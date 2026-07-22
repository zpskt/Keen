# src/wechat_work_utils.py
from datetime import datetime

import requests
import json
import time
from typing import Dict, Any, List, Optional
import os
from datetime import datetime
class WeChatWorkNotifier:
    """企业微信机器人通知封装（个人可用）"""

    def __init__(self, webhook_url:  str = None):
        """
        初始化企业微信机器人
        :param webhook_url: 机器人的 Webhook 地址
        """
        if webhook_url is None:
            webhook_url = os.getenv('WECHAT_WORK_WEBHOOK', '')

        if not webhook_url:
            raise ValueError("请设置 WECHAT_WORK_WEBHOOK 环境变量或传入 webhook_url 参数")

        self.webhook_url = webhook_url

    def send_text(self, content: str, mentioned_list: List[str] = None,
                  mentioned_mobile_list: List[str] = None) -> Dict[str, Any]:
        """
        发送文本消息
        :param content: 文本内容
        :param mentioned_list: @的成员列表（userid）
        :param mentioned_mobile_list: @的手机号列表
        """
        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }

            if mentioned_list:
                data["text"]["mentioned_list"] = mentioned_list
            if mentioned_mobile_list:
                data["text"]["mentioned_mobile_list"] = mentioned_mobile_list

            response = requests.post(self.webhook_url, json=data, timeout=5)
            result = response.json()

            if result.get('errcode') == 0:
                return {'success': True, 'message': '发送成功'}
            else:
                return {'success': False, 'message': result.get('errmsg', '未知错误')}

        except Exception as e:
            return {'success': False, 'message': str(e)}

    def send_markdown(self, content: str) -> Dict[str, Any]:
        """
        发送 Markdown 消息（支持更丰富的格式）
        :param content: Markdown 格式内容
        """
        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }

            response = requests.post(self.webhook_url, json=data, timeout=5)
            result = response.json()

            if result.get('errcode') == 0:
                return {'success': True, 'message': '发送成功'}
            else:
                return {'success': False, 'message': result.get('errmsg', '未知错误')}

        except Exception as e:
            return {'success': False, 'message': str(e)}

    def send_image(self, image_base64: str, md5: str) -> Dict[str, Any]:
        """
        发送图片消息
        :param image_base64: 图片的 Base64 编码
        :param md5: 图片的 MD5 值
        """
        try:
            data = {
                "msgtype": "image",
                "image": {
                    "base64": image_base64,
                    "md5": md5
                }
            }

            response = requests.post(self.webhook_url, json=data, timeout=5)
            result = response.json()

            if result.get('errcode') == 0:
                return {'success': True, 'message': '发送成功'}
            else:
                return {'success': False, 'message': result.get('errmsg', '未知错误')}

        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ===== 辅助函数：发送跌倒告警通知 =====
    def send_fall_alert_notification(self, event_data: dict, event_id: int, image_url: str):
        """
        发送跌倒告警通知到企业微信
        :param event_data: 事件数据
        :param event_id: 事件ID
        :param image_url: 图片URL
        """

        # 从 metadata 中提取信息
        metadata = event_data.get('metadata', {})
        location = event_data.get('location', '未知位置')
        confidence = event_data.get('confidence', 0.0)
        camera_id = metadata.get('camera_id', '未知')
        # 解析时间
        try:
            event_time = event_data.get('event_time', '')
            if event_time:
                # 处理 ISO 格式时间
                dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                event_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                event_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except:
            event_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 构建 Markdown 消息内容
        markdown_content = f"""
    # 🚨 <font color="warning">跌倒事件告警</font>

    > **📍 地点**：{location}
    > **🕐 时间**：{event_time_str}
    > **📊 置信度**：<font color="info">{confidence * 100:.1f}%</font>
    > **📹 摄像头**：{camera_id}
    > **📋 事件ID**：{event_id}
    > **📂 来源**：{event_data.get('source', '未知')}

    ---
    [📷 **点击查看现场图片**]({image_url})

    ⚠️ **请立即确认人员安全！**
        """

        # 发送通知（使用 self 调用自己的方法）
        result = self.send_markdown(markdown_content)

        if result['success']:
            print(f"📱 企业微信通知发送成功，事件ID: {event_id}")
        else:
            print(f"⚠️ 企业微信通知发送失败: {result['message']}")

        return result


# ===== 快速测试 =====
if __name__ == '__main__':
    # 替换为你的企业微信机器人 Webhook

    notifier = WeChatWorkNotifier()

    # 测试文本消息
    result = notifier.send_text("测试消息：跌倒检测服务正常运行")
    print(result)

    # 测试 Markdown（更美观）
    # result = notifier.send_markdown("## 测试消息\n这是一条 **Markdown** 格式消息")
    # print(result)