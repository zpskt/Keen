#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：Keen 
@File    ：app.py.py
@IDE     ：PyCharm 
@Author  ：张鹏
@Date    ：2026/7/22 22:30 
@Description： 
'''
# app.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from PIL import Image
from io import BytesIO

# ===== 页面配置 =====
st.set_page_config(
    page_title="跌倒检测监控面板",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== API 配置 =====
API_BASE_URL = "http://localhost:8080"

# ===== 自定义样式 =====
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-card-red {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-card-green {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .event-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #f5576c;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .event-card-resolved {
        border-left-color: #4facfe;
        background: #f8f9fa;
        opacity: 0.7;
    }
</style>
""", unsafe_allow_html=True)

# ===== 标题 =====
st.title("🚨 跌倒检测实时监控系统")
st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源: {API_BASE_URL}")

# ===== 侧边栏 =====
with st.sidebar:
    st.header("⚙️ 控制面板")

    # 自动刷新开关
    auto_refresh = st.checkbox("🔄 自动刷新", value=True)
    refresh_interval = st.slider("刷新间隔（秒）", 5, 60, 10)

    # 状态筛选
    st.subheader("🔍 筛选条件")
    status_filter = st.selectbox(
        "事件状态",
        ["全部", "待处理", "处理中", "已完成", "失败"]
    )

    # 时间筛选
    date_filter = st.selectbox(
        "时间范围",
        ["全部", "今天", "最近7天", "最近30天"]
    )

    st.divider()

    # 统计信息
    st.subheader("📊 快捷操作")
    if st.button("🔄 手动刷新", use_container_width=True):
        st.rerun()

    if st.button("📤 导出报表 (CSV)", use_container_width=True):
        st.info("导出功能开发中...")


# ===== 辅助函数 =====
def fetch_events(limit=100):
    """获取事件列表"""
    try:
        response = requests.get(f"{API_BASE_URL}/events?limit={limit}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("events", [])
        else:
            st.error(f"API 请求失败: {response.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        st.error(f"❌ 无法连接到服务: {API_BASE_URL}")
        st.info("请确保 fall_event_server.py 正在运行")
        return []
    except Exception as e:
        st.error(f"获取事件失败: {str(e)}")
        return []


def fetch_statistics():
    """获取统计数据"""
    try:
        response = requests.get(f"{API_BASE_URL}/events/statistics", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def filter_events(events, status, date_range):
    """筛选事件"""
    if not events:
        return []

    df = pd.DataFrame(events)

    # 状态筛选
    status_map = {"全部": None, "待处理": 0, "处理中": 1, "已完成": 2, "失败": 3}
    if status != "全部":
        df = df[df["status"] == status_map[status]]

    # 时间筛选
    if date_range != "全部" and not df.empty:
        df["event_time"] = pd.to_datetime(df["event_time"])
        now = datetime.now()
        if date_range == "今天":
            df = df[df["event_time"].dt.date == now.date()]
        elif date_range == "最近7天":
            df = df[df["event_time"] >= now - timedelta(days=7)]
        elif date_range == "最近30天":
            df = df[df["event_time"] >= now - timedelta(days=30)]

    return df.to_dict("records")


# ===== 获取数据 =====
events = fetch_events(200)
stats = fetch_statistics()
filtered_events = filter_events(events, status_filter, date_filter)

# ===== 统计卡片 =====
if stats:
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2>{stats.get('total', 0)}</h2>
            <p>📊 总事件</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card-red">
            <h2>{stats.get('today', 0)}</h2>
            <p>📅 今日事件</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card-orange">
            <h2>{stats.get('pending', 0)}</h2>
            <p>⏳ 待处理</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card-green">
            <h2>{stats.get('completed', 0)}</h2>
            <p>✅ 已完成</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <h2>{stats.get('failed', 0)}</h2>
            <p>❌ 失败</p>
        </div>
        """, unsafe_allow_html=True)

# ===== 事件列表 =====
st.subheader(f"📋 事件列表 ({len(filtered_events)} 条)")

if filtered_events:
    # 转换为 DataFrame 展示
    df_display = pd.DataFrame(filtered_events)

    # 选择要显示的列
    columns_to_show = ["id", "event_time", "source", "status", "event_type"]
    display_df = df_display[columns_to_show].copy()

    # 状态映射
    status_map = {0: "🟡 待处理", 1: "🔵 处理中", 2: "🟢 已完成", 3: "🔴 失败"}
    display_df["status"] = display_df["status"].map(status_map)

    # 显示表格
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "id": "ID",
            "event_time": "事件时间",
            "source": "来源",
            "status": "状态",
            "event_type": "事件类型"
        }
    )

    # ===== 详细卡片视图 =====
    st.subheader("📇 事件详情")

    # 分页
    page_size = 5
    total_pages = max(1, (len(filtered_events) + page_size - 1) // page_size)
    page = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1)

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, len(filtered_events))

    for event in filtered_events[start_idx:end_idx]:
        metadata = event.get("metadata", {})
        status_text = ["待处理", "处理中", "已完成", "失败"][event.get("status", 0)]
        status_color = ["#f5576c", "#4facfe", "#52c41a", "#faad14"][event.get("status", 0)]

        with st.container():
            cols = st.columns([3, 1])

            with cols[0]:
                st.markdown(f"""
                <div style="border-left: 4px solid {status_color}; padding: 10px; background: #f8f9fa; border-radius: 4px; margin: 5px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold;">📍 {metadata.get('location', '未知位置')}</span>
                        <span style="color: {status_color}; font-weight: bold;">{status_text}</span>
                    </div>
                    <div style="font-size: 14px; color: #666; margin-top: 5px;">
                        🕐 {event.get('event_time', '')} &nbsp;|&nbsp; 
                        📊 置信度: {metadata.get('confidence', 0) * 100:.1f}% &nbsp;|&nbsp;
                        📹 {metadata.get('camera_id', '未知摄像头')} &nbsp;|&nbsp;
                        🆔 ID: {event.get('id')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with cols[1]:
                # 查看图片按钮
                image_url = event.get("image_url", "")
                if image_url:
                    if st.button("📷 查看图片", key=f"img_{event.get('id')}"):
                        st.session_state[f"show_img_{event.get('id')}"] = True

                # 状态更新按钮
                if event.get("status") == 0:
                    if st.button("✅ 确认处理", key=f"resolve_{event.get('id')}"):
                        try:
                            response = requests.patch(
                                f"{API_BASE_URL}/events/{event.get('id')}/status",
                                params={"status": 2}
                            )
                            if response.status_code == 200:
                                st.success(f"事件 {event.get('id')} 已标记为已完成")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"更新失败: {str(e)}")

            # 显示图片弹窗
            if st.session_state.get(f"show_img_{event.get('id')}", False):
                try:
                    img_response = requests.get(image_url, timeout=10)
                    if img_response.status_code == 200:
                        img = Image.open(BytesIO(img_response.content))
                        st.image(img, caption=f"事件 {event.get('id')} 现场图片", use_container_width=True)
                    else:
                        st.warning(f"无法加载图片: {image_url}")
                except:
                    st.warning(f"图片加载失败")
                if st.button("关闭图片", key=f"close_img_{event.get('id')}"):
                    st.session_state[f"show_img_{event.get('id')}"] = False
                    st.rerun()

            st.divider()

else:
    st.info("📭 暂无事件数据，请等待算法推送或手动发送测试事件")

# ===== 自动刷新 =====
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

# ===== 底部 =====
st.divider()
st.caption("💡 提示: 点击「确认处理」可更新事件状态 | 图片会自动缓存显示")
