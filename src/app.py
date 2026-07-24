#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：Keen 
@File    ：app.py
@IDE     ：PyCharm
@Author  ：张鹏
@Date    ：2026/7/22 22:30
@Description：跌倒检测监控系统 - 包含事件监控和人员管理
'''
# app.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import time
import base64
from PIL import Image
from io import BytesIO

from logger_utils import get_logger

# ===== 初始化日志 =====
logger = get_logger('app')

# ===== 页面配置 =====
st.set_page_config(
    page_title="跌倒检测监控系统",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== API 配置 =====
API_BASE_URL = "http://localhost:8080"
PERSON_API_URL = f"{API_BASE_URL}/api/persons"

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
    .person-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
        margin: 10px 0;
    }
    .person-card img {
        border-radius: 50%;
        width: 120px;
        height: 120px;
        object-fit: cover;
    }
</style>
""", unsafe_allow_html=True)

# ===== 侧边栏导航 =====
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/security-checked--v1.png", width=60)
    st.title("🚨 跌倒检测系统")

    # 导航菜单
    menu = st.radio(
        "📋 导航",
        ["📊 事件监控", "👤 人员管理"]
    )

    st.divider()

# ============================================================
# ===== 页面1：事件监控 =====
# ============================================================
if menu == "📊 事件监控":
    st.title("🚨 跌倒检测实时监控系统")
    st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源: {API_BASE_URL}")

    # ===== 侧边栏控制 =====
    with st.sidebar:
        st.header("⚙️ 控制面板")

        auto_refresh = st.checkbox("🔄 自动刷新", value=True)
        refresh_interval = st.slider("刷新间隔（秒）", 5, 60, 10)

        st.subheader("🔍 筛选条件")
        status_filter = st.selectbox(
            "事件状态",
            ["全部", "待处理", "处理中", "已完成", "失败"]
        )

        date_filter = st.selectbox(
            "时间范围",
            ["全部", "今天", "最近7天", "最近30天"]
        )

        st.divider()

        if st.button("🔄 手动刷新", use_container_width=True):
            st.rerun()


    # ===== 辅助函数 =====
    def fetch_events(limit=100):
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
            st.info("请确保 fall_event_server_api.py 正在运行")
            return []
        except Exception as e:
            st.error(f"获取事件失败: {str(e)}")
            return []


    def fetch_statistics():
        try:
            response = requests.get(f"{API_BASE_URL}/events/statistics", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None


    def filter_events(events, status, date_range):
        if not events:
            return []

        df = pd.DataFrame(events)

        status_map = {"全部": None, "待处理": 0, "处理中": 1, "已完成": 2, "失败": 3}
        if status != "全部":
            df = df[df["status"] == status_map[status]]

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
        df_display = pd.DataFrame(filtered_events)
        columns_to_show = ["id", "event_time", "source", "status", "event_type"]
        display_df = df_display[columns_to_show].copy()

        status_map = {0: "🟡 待处理", 1: "🔵 处理中", 2: "🟢 已完成", 3: "🔴 失败"}
        display_df["status"] = display_df["status"].map(status_map)

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

        st.subheader("📇 事件详情")

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
                    image_url = event.get("image_url", "")
                    if image_url:
                        if st.button("📷 查看图片", key=f"img_{event.get('id')}"):
                            st.session_state[f"show_img_{event.get('id')}"] = True

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

    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

# ============================================================
# ===== 页面2：人员管理 =====
# ============================================================
else:
    st.title("👤 人员管理系统")

    # ===== 人员管理侧边栏 =====
    with st.sidebar:
        st.header("👤 人员管理")
        person_action = st.radio(
            "选择操作",
            ["📋 人员列表", "➕ 添加人员", "📊 统计信息"]
        )


    # ===== 辅助函数 =====
    def fetch_persons():
        try:
            response = requests.get(PERSON_API_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("persons", [])
            return []
        except Exception as e:
            st.error(f"获取人员列表失败: {e}")
            return []


    def fetch_person_statistics():
        try:
            response = requests.get(f"{PERSON_API_URL}/statistics", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            return {}


    def create_person(data, photo_base64):
        try:
            payload = {**data, "photo_base64": photo_base64}
            response = requests.post(PERSON_API_URL, json=payload, timeout=10)
            print("创建结果:", response.status_code, response.text)
            # 如果是 200，成功
            if response.status_code == 200:
                return True, "创建成功"
            else:
                # 尝试从响应中获取详细错误信息
                try:
                    error_detail = response.json().get('detail', response.text)
                except:
                    error_detail = response.text
                # 如果是列表，转为 JSON 字符串
                if isinstance(error_detail, list):
                    error_msg = json.dumps(error_detail, ensure_ascii=False)
                else:
                    error_msg = str(error_detail)
                # 返回错误信息，而不是抛出异常
                return False, error_msg

        except Exception as e:
            return False, str(e)


    def update_person(person_id, data, photo_base64):
        try:
            payload = {**data, "photo_base64": photo_base64}
            response = requests.put(f"{PERSON_API_URL}/{person_id}", json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            st.error(f"更新失败: {e}")
            return False


    def delete_person(person_id):
        try:
            response = requests.delete(f"{PERSON_API_URL}/{person_id}", timeout=5)
            return response.status_code == 200
        except Exception as e:
            st.error(f"删除失败: {e}")
            return False


    # app.py 中替换 display_photo 函数

    def display_photo(photo_url, width=150):
        """
        显示照片
        支持 OSS URL（通过代理）和普通 URL
        """
        logger.info(f"显示照片: {photo_url}")
        if not photo_url or photo_url == "None" or photo_url.strip() == "":
            st.info("无照片")
            return False

        try:
            # 如果是 OSS 默认域名，使用代理
            if 'oss-cn-beijing.aliyuncs.com' in photo_url:
                from urllib.parse import quote
                encoded_url = quote(photo_url, safe='')
                proxy_url = f"{API_BASE_URL}/api/proxy/image?url={encoded_url}"

                # 通过代理获取图片数据
                response = requests.get(proxy_url, timeout=10)
                if response.status_code == 200:
                    # 从二进制数据解析图片
                    img = Image.open(BytesIO(response.content))
                    st.image(img, width=width)
                    return True
                else:
                    st.warning(f"图片加载失败: HTTP {response.status_code}")
                    return False

            else:
                # 普通 URL 直接显示
                st.image(photo_url, width=width)
                return True

        except Exception as e:
            st.warning(f"图片加载异常: {e}")
            return False


    # ===== 统计信息 =====
    if person_action == "📊 统计信息":
        st.subheader("📊 人员统计")

        stats = fetch_person_statistics()

        if stats:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👤 总人数", stats.get('total', 0))
            col2.metric("👨 男性", stats.get('male', 0))
            col3.metric("👩 女性", stats.get('female', 0))
            col4.metric("🏠 房间数", stats.get('rooms', 0))
        else:
            st.info("暂无统计数据")

    # ===== 添加人员 =====
    elif person_action == "➕ 添加人员":
        st.subheader("➕ 添加新人员")

        with st.form("add_person_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("姓名 *")
                age = st.number_input("年龄", min_value=0, max_value=150, value=70)
                gender = st.selectbox("性别", ["未知", "男", "女"])
                room_number = st.text_input("房间号")
                bed_number = st.text_input("床位号")
                floor = st.text_input("楼层")
                building = st.text_input("楼栋")

            with col2:
                guardian_name = st.text_input("监护人姓名")
                guardian_phone = st.text_input("监护人电话")
                guardian_relationship = st.text_input("监护关系")
                medical_history = st.text_area("病史")
                special_notes = st.text_area("特殊注意事项")

            photo_file = st.file_uploader("上传照片", type=['jpg', 'jpeg', 'png'])
            photo_base64 = None

            if photo_file:
                photo_base64 = base64.b64encode(photo_file.read()).decode('utf-8')
                st.success("✅ 照片已上传")

            submitted = st.form_submit_button("💾 保存")

            if submitted:
                if not name:
                    st.error("姓名不能为空")
                else:
                    data = {
                        "name": name,
                        "age": age,
                        "gender": gender,
                        "room_number": room_number,
                        "bed_number": bed_number,
                        "floor": floor,
                        "building": building,
                        "guardian_name": guardian_name,
                        "guardian_phone": guardian_phone,
                        "guardian_relationship": guardian_relationship,
                        "medical_history": medical_history,
                        "special_notes": special_notes
                    }
                    success, message = create_person(data, photo_base64)
                    if success:
                        st.success("✅ 人员创建成功！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 创建失败:"+ message)

    # ===== 人员列表 =====
    else:
        st.subheader("📋 人员列表")

        search_keyword = st.text_input("🔍 搜索人员（姓名/房间号/监护人）")

        persons = fetch_persons()

        if search_keyword:
            persons = [p for p in persons if
                       search_keyword in p.get('name', '') or
                       search_keyword in p.get('room_number', '') or
                       search_keyword in p.get('guardian_name', '')]

        if not persons:
            st.info("暂无人员数据")
        else:
            st.write(f"共 {len(persons)} 人")

            # 卡片视图
            cols_per_row = 4
            rows = (len(persons) + cols_per_row - 1) // cols_per_row

            for row in range(rows):
                cols = st.columns(cols_per_row)
                for col_idx in range(cols_per_row):
                    person_idx = row * cols_per_row + col_idx
                    if person_idx >= len(persons):
                        break

                    person = persons[person_idx]
                    with cols[col_idx]:
                        with st.container():
                            st.markdown('<div class="person-card">', unsafe_allow_html=True)

                            if person.get('photo_path'):
                                display_photo(person['photo_path'], width=150)
                            else:
                                st.info("无照片")

                            st.markdown(f"""
                            **👤 {person.get('name', '未知')}**
                            - 🆔 ID: {person.get('id')}
                            - 🏠 房间: {person.get('room_number', '未设置')}
                            - 📞 监护人: {person.get('guardian_name', '未设置')}
                            """)

                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("✏️", key=f"edit_{person.get('id')}"):
                                    st.session_state['editing_person'] = person
                                    st.session_state['show_edit_dialog'] = True
                            with col_btn2:
                                if st.button("🗑️", key=f"del_{person.get('id')}"):
                                    if delete_person(person.get('id')):
                                        st.success(f"已删除 {person.get('name')}")
                                        st.rerun()
                                    else:
                                        st.error("删除失败")

                            st.markdown('</div>', unsafe_allow_html=True)

            # ===== 编辑对话框 =====
            if st.session_state.get('show_edit_dialog', False):
                person = st.session_state.get('editing_person', {})

                with st.expander(f"✏️ 编辑 {person.get('name', '')}", expanded=True):
                    with st.form("edit_person_form"):
                        col1, col2 = st.columns(2)

                        with col1:
                            edit_name = st.text_input("姓名", value=person.get('name', ''))
                            edit_age = st.number_input("年龄", min_value=0, max_value=150,
                                                       value=person.get('age', 70))
                            edit_gender = st.selectbox("性别", ["未知", "男", "女"],
                                                       index=["未知", "男", "女"].index(person.get('gender', '未知')))
                            edit_room = st.text_input("房间号", value=person.get('room_number', ''))
                            edit_bed = st.text_input("床位号", value=person.get('bed_number', ''))

                        with col2:
                            edit_guardian = st.text_input("监护人", value=person.get('guardian_name', ''))
                            edit_phone = st.text_input("监护人电话", value=person.get('guardian_phone', ''))
                            edit_relation = st.text_input("监护关系", value=person.get('guardian_relationship', ''))
                            edit_history = st.text_area("病史", value=person.get('medical_history', ''))
                            edit_notes = st.text_area("备注", value=person.get('special_notes', ''))

                        edit_photo_file = st.file_uploader("更换照片", type=['jpg', 'jpeg', 'png'])
                        edit_photo_base64 = None
                        if edit_photo_file:
                            edit_photo_base64 = base64.b64encode(edit_photo_file.read()).decode('utf-8')

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.form_submit_button("💾 保存"):
                                data = {
                                    "name": edit_name,
                                    "age": edit_age,
                                    "gender": edit_gender,
                                    "room_number": edit_room,
                                    "bed_number": edit_bed,
                                    "guardian_name": edit_guardian,
                                    "guardian_phone": edit_phone,
                                    "guardian_relationship": edit_relation,
                                    "medical_history": edit_history,
                                    "special_notes": edit_notes
                                }
                                if update_person(person.get('id'), data, edit_photo_base64):
                                    st.success("✅ 更新成功！")
                                    st.session_state['show_edit_dialog'] = False
                                    st.rerun()
                                else:
                                    st.error("❌ 更新失败")

                        with col_btn2:
                            if st.form_submit_button("❌ 取消"):
                                st.session_state['show_edit_dialog'] = False
                                st.rerun()

# ===== 底部 =====
st.divider()
st.caption("💡 提示: 事件监控 | 人员管理 | 实时告警")