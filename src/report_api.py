# src/report_api.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import csv
import io
from collections import Counter, defaultdict
from fastapi.responses import StreamingResponse

from logger_utils import get_logger
from db_utils import Database
from person_manager import PersonManager

logger = get_logger('report_api')

router = APIRouter(prefix="/api/reports", tags=["数据报表"])

db = Database()
person_manager = PersonManager()


def parse_time(time_str: str) -> datetime:
    """解析时间字符串"""
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except:
        return datetime.now()


def get_events_by_date_range(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """按日期范围获取事件"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT *
                       FROM fall_events
                       WHERE event_time BETWEEN ? AND ?
                         AND status != 3
                       ORDER BY event_time DESC
                       """, (start_date, end_date))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_events_by_period(period: str) -> List[Dict[str, Any]]:
    """按周期获取事件"""
    now = datetime.now()
    if period == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == 'week':
        start = now - timedelta(days=7)
        end = now
    elif period == 'month':
        start = now - timedelta(days=30)
        end = now
    elif period == 'quarter':
        start = now - timedelta(days=90)
        end = now
    else:
        start = now - timedelta(days=7)
        end = now

    return get_events_by_date_range(start.isoformat(), end.isoformat())


# ===== 日报 =====
@router.get("/daily")
async def get_daily_report(date: Optional[str] = Query(None, description="日期，格式: YYYY-MM-DD")):
    """
    日报统计
    返回：今日事件总数、待处理数、已处理数、各状态分布
    """
    try:
        if date:
            target_date = datetime.fromisoformat(date)
        else:
            target_date = datetime.now()

        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        events = get_events_by_date_range(start.isoformat(), end.isoformat())

        # 统计
        total = len(events)
        pending = sum(1 for e in events if e.get('status') == 0)
        processing = sum(1 for e in events if e.get('status') == 1)
        completed = sum(1 for e in events if e.get('status') == 2)
        failed = sum(1 for e in events if e.get('status') == 3)

        # 按小时分布
        hour_distribution = [0] * 24
        for e in events:
            try:
                hour = parse_time(e.get('event_time', '')).hour
                hour_distribution[hour] += 1
            except:
                pass

        # 包含人员的数量
        with_person = sum(1 for e in events if e.get('person_id') is not None)

        return {
            "code": 0,
            "data": {
                "date": target_date.strftime('%Y-%m-%d'),
                "summary": {
                    "total": total,
                    "pending": pending,
                    "processing": processing,
                    "completed": completed,
                    "failed": failed
                },
                "rate": {
                    "completion_rate": round(completed / total * 100, 2) if total > 0 else 0,
                    "with_person_rate": round(with_person / total * 100, 2) if total > 0 else 0
                },
                "hour_distribution": hour_distribution
            }
        }

    except Exception as e:
        logger.error(f"获取日报失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 周报 =====
@router.get("/weekly")
async def get_weekly_report():
    """
    周报统计
    返回：近7天每日事件数、平均事件数、趋势
    """
    try:
        now = datetime.now()
        events = []

        # 获取近7天数据
        day_stats = []
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

            day_events = get_events_by_date_range(start.isoformat(), end.isoformat())
            day_stats.append({
                "date": day.strftime('%Y-%m-%d'),
                "total": len(day_events),
                "pending": sum(1 for e in day_events if e.get('status') == 0),
                "completed": sum(1 for e in day_events if e.get('status') == 2)
            })
            events.extend(day_events)

        # 总统计
        total = len(events)
        pending = sum(1 for e in events if e.get('status') == 0)
        completed = sum(1 for e in events if e.get('status') == 2)

        # 计算平均值
        avg_total = sum(d['total'] for d in day_stats) / 7 if day_stats else 0
        avg_completed = sum(d['completed'] for d in day_stats) / 7 if day_stats else 0

        # 趋势方向
        if len(day_stats) >= 2:
            trend = day_stats[-1]['total'] - day_stats[0]['total']
        else:
            trend = 0

        return {
            "code": 0,
            "data": {
                "period": f"{day_stats[0]['date']} ~ {day_stats[-1]['date']}" if day_stats else "",
                "summary": {
                    "total": total,
                    "pending": pending,
                    "completed": completed,
                    "avg_daily": round(avg_total, 1),
                    "avg_completed_daily": round(avg_completed, 1),
                    "trend": "上升" if trend > 0 else "下降" if trend < 0 else "平稳",
                    "trend_value": trend
                },
                "daily_detail": day_stats
            }
        }

    except Exception as e:
        logger.error(f"获取周报失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 月报 =====
@router.get("/monthly")
async def get_monthly_report(
        year: Optional[int] = Query(None, description="年份"),
        month: Optional[int] = Query(None, description="月份")
):
    """
    月报统计
    返回：当月每日事件分布、各状态汇总
    """
    try:
        now = datetime.now()
        target_year = year or now.year
        target_month = month or now.month

        # 获取当月第一天和最后一天
        first_day = datetime(target_year, target_month, 1)
        if target_month == 12:
            last_day = datetime(target_year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(target_year, target_month + 1, 1) - timedelta(days=1)

        events = get_events_by_date_range(first_day.isoformat(), last_day.isoformat())

        # 按天统计
        daily_stats = defaultdict(lambda: {"total": 0, "pending": 0, "completed": 0, "fall": 0})
        for e in events:
            try:
                day = parse_time(e.get('event_time', '')).strftime('%Y-%m-%d')
                daily_stats[day]['total'] += 1
                if e.get('status') == 0:
                    daily_stats[day]['pending'] += 1
                elif e.get('status') == 2:
                    daily_stats[day]['completed'] += 1
                # 检测跌倒事件（event_type 包含 fall）
                if 'fall' in e.get('event_type', '').lower():
                    daily_stats[day]['fall'] += 1
            except:
                pass

        # 排序
        daily_list = sorted([{"date": k, **v} for k, v in daily_stats.items()], key=lambda x: x['date'])

        # 汇总
        total = len(events)
        pending = sum(1 for e in events if e.get('status') == 0)
        completed = sum(1 for e in events if e.get('status') == 2)

        return {
            "code": 0,
            "data": {
                "year": target_year,
                "month": target_month,
                "days_in_month": (last_day - first_day).days + 1,
                "summary": {
                    "total": total,
                    "pending": pending,
                    "completed": completed,
                    "completion_rate": round(completed / total * 100, 2) if total > 0 else 0
                },
                "daily_detail": daily_list
            }
        }

    except Exception as e:
        logger.error(f"获取月报失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 趋势分析 =====
@router.get("/trend")
async def get_trend_analysis(
        days: int = Query(30, description="分析天数", ge=1, le=365),
        granularity: str = Query("day", description="粒度: day/hour/week", regex="^(day|hour|week)$")
):
    """
    趋势分析
    返回：事件数量随时间变化的趋势
    """
    try:
        now = datetime.now()
        start = now - timedelta(days=days)
        events = get_events_by_date_range(start.isoformat(), now.isoformat())

        if granularity == "hour":
            # 按小时聚合（最近24小时）
            start_hour = now - timedelta(hours=24)
            events = get_events_by_date_range(start_hour.isoformat(), now.isoformat())
            buckets = [f"{h:02d}:00" for h in range(24)]

            stats = {h: {"total": 0, "fall": 0, "pending": 0} for h in range(24)}
            for e in events:
                try:
                    hour = parse_time(e.get('event_time', '')).hour
                    stats[hour]['total'] += 1
                    if 'fall' in e.get('event_type', '').lower():
                        stats[hour]['fall'] += 1
                    if e.get('status') == 0:
                        stats[hour]['pending'] += 1
                except:
                    pass

            trend_data = [{"time": f"{h:02d}:00", **stats[h]} for h in range(24)]

        elif granularity == "week":
            # 按周聚合
            buckets = []
            stats = {}
            for i in range(days // 7 + 1):
                week_start = start + timedelta(days=i * 7)
                week_end = min(week_start + timedelta(days=6), now)
                week_key = week_start.strftime('%Y-%m-%d')
                stats[week_key] = {"total": 0, "fall": 0, "pending": 0}

                week_events = get_events_by_date_range(week_start.isoformat(), week_end.isoformat())
                for e in week_events:
                    stats[week_key]['total'] += 1
                    if 'fall' in e.get('event_type', '').lower():
                        stats[week_key]['fall'] += 1
                    if e.get('status') == 0:
                        stats[week_key]['pending'] += 1

            trend_data = [{"time": k, **v} for k, v in stats.items()]

        else:
            # 按天聚合（默认）
            stats = defaultdict(lambda: {"total": 0, "fall": 0, "pending": 0})
            for e in events:
                try:
                    day = parse_time(e.get('event_time', '')).strftime('%Y-%m-%d')
                    stats[day]['total'] += 1
                    if 'fall' in e.get('event_type', '').lower():
                        stats[day]['fall'] += 1
                    if e.get('status') == 0:
                        stats[day]['pending'] += 1
                except:
                    pass

            trend_data = [{"time": k, **v} for k, v in sorted(stats.items())]

        # 计算移动平均（7天）
        if len(trend_data) > 7:
            for i in range(len(trend_data)):
                if i >= 7:
                    avg = sum(trend_data[j]['total'] for j in range(i - 6, i + 1)) / 7
                    trend_data[i]['ma7'] = round(avg, 1)
                else:
                    trend_data[i]['ma7'] = None

        return {
            "code": 0,
            "data": {
                "granularity": granularity,
                "days": days,
                "total_events": len(events),
                "trend": trend_data
            }
        }

    except Exception as e:
        logger.error(f"获取趋势分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 高发时段分析 =====
@router.get("/peak-hours")
async def get_peak_hours_analysis(
        days: int = Query(30, description="分析天数", ge=1, le=365)
):
    """
    高发时段分析
    返回：24小时中每个时段的事件分布，识别高峰期
    """
    try:
        now = datetime.now()
        start = now - timedelta(days=days)
        events = get_events_by_date_range(start.isoformat(), now.isoformat())

        # 按小时统计
        hour_stats = [{"hour": h, "total": 0, "fall": 0, "pending": 0} for h in range(24)]
        hour_map = {h: i for i, h in enumerate(range(24))}

        for e in events:
            try:
                hour = parse_time(e.get('event_time', '')).hour
                hour_stats[hour_map[hour]]['total'] += 1
                if 'fall' in e.get('event_type', '').lower():
                    hour_stats[hour_map[hour]]['fall'] += 1
                if e.get('status') == 0:
                    hour_stats[hour_map[hour]]['pending'] += 1
            except:
                pass

        # 计算平均值和高峰判定
        total_events = sum(h['total'] for h in hour_stats)
        avg = total_events / 24 if total_events > 0 else 0

        for h in hour_stats:
            h['avg'] = round(avg, 1)
            h['is_peak'] = h['total'] > avg * 1.5  # 超过平均值1.5倍视为高峰

        # 找出高峰时段
        peak_hours = [h for h in hour_stats if h['is_peak']]

        return {
            "code": 0,
            "data": {
                "days": days,
                "total_events": total_events,
                "avg_per_hour": round(avg, 1),
                "hourly": hour_stats,
                "peak_hours": peak_hours,
                "peak_hours_count": len(peak_hours)
            }
        }

    except Exception as e:
        logger.error(f"获取高发时段分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 高发区域分析 =====
@router.get("/hotspots")
async def get_hotspots_analysis(
        days: int = Query(30, description="分析天数", ge=1, le=365)
):
    """
    高发区域分析
    返回：各房间/区域的事件分布，识别高危区域
    """
    try:
        now = datetime.now()
        start = now - timedelta(days=days)
        events = get_events_by_date_range(start.isoformat(), now.isoformat())

        # 从 metadata 中提取位置信息
        location_stats = defaultdict(lambda: {"total": 0, "fall": 0, "pending": 0})

        for e in events:
            try:
                metadata = json.loads(e.get('metadata', '{}')) if isinstance(e.get('metadata'), str) else e.get(
                    'metadata', {})
                location = metadata.get('location', '未知位置')

                # 提取房间号（如 "301室" -> "301"）
                import re
                room_match = re.search(r'(\d+)', location)
                room = room_match.group(1) if room_match else location

                location_stats[room]['total'] += 1
                if 'fall' in e.get('event_type', '').lower():
                    location_stats[room]['fall'] += 1
                if e.get('status') == 0:
                    location_stats[room]['pending'] += 1
            except:
                pass

        # 按总数排序
        sorted_stats = sorted(
            [{"location": k, **v} for k, v in location_stats.items()],
            key=lambda x: x['total'],
            reverse=True
        )

        total_events = sum(s['total'] for s in sorted_stats)
        avg = total_events / len(sorted_stats) if sorted_stats else 0

        # 标记高危区域（超过平均值2倍）
        for s in sorted_stats:
            s['is_hotspot'] = s['total'] > avg * 2
            s['risk_level'] = "高危" if s['total'] > avg * 2 else "中危" if s['total'] > avg else "低危"

        return {
            "code": 0,
            "data": {
                "days": days,
                "total_events": total_events,
                "locations_count": len(sorted_stats),
                "hotspots": [s for s in sorted_stats if s['is_hotspot']],
                "location_stats": sorted_stats
            }
        }

    except Exception as e:
        logger.error(f"获取高发区域分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 人员维度统计 =====
@router.get("/person")
async def get_person_report(
        days: int = Query(30, description="分析天数", ge=1, le=365)
):
    """
    人员维度统计
    返回：各人员的跌倒事件数、处理状态
    """
    try:
        now = datetime.now()
        start = now - timedelta(days=days)
        events = get_events_by_date_range(start.isoformat(), now.isoformat())

        # 按人员统计
        person_stats = defaultdict(lambda: {
            "total": 0,
            "pending": 0,
            "completed": 0,
            "person_name": "未知"
        })

        for e in events:
            person_id = e.get('person_id')
            if person_id:
                person_name = e.get('person_name', '未知')
                person_stats[person_id]['total'] += 1
                person_stats[person_id]['person_name'] = person_name
                if e.get('status') == 0:
                    person_stats[person_id]['pending'] += 1
                elif e.get('status') == 2:
                    person_stats[person_id]['completed'] += 1

        # 转为列表并排序
        sorted_stats = sorted(
            [{"person_id": k, **v} for k, v in person_stats.items()],
            key=lambda x: x['total'],
            reverse=True
        )

        return {
            "code": 0,
            "data": {
                "days": days,
                "total_events": len(events),
                "persons_with_events": len(sorted_stats),
                "person_stats": sorted_stats
            }
        }

    except Exception as e:
        logger.error(f"获取人员统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 导出报表 =====
@router.get("/export")
async def export_report(
        start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
        end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
        format: str = Query("csv", description="导出格式: csv/excel")
):
    """
    导出报表为 CSV
    """
    try:
        events = get_events_by_date_range(start_date, end_date)

        # 创建 CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow([
            "ID", "事件类型", "来源", "事件时间", "接收时间",
            "状态", "人员ID", "人员姓名", "图片URL", "位置", "置信度"
        ])

        # 写入数据
        for e in events:
            metadata = json.loads(e.get('metadata', '{}')) if isinstance(e.get('metadata'), str) else e.get('metadata',
                                                                                                            {})
            writer.writerow([
                e.get('id'),
                e.get('event_type'),
                e.get('source'),
                e.get('event_time'),
                e.get('received_time'),
                ["待处理", "处理中", "已完成", "失败"][e.get('status', 0)],
                e.get('person_id'),
                e.get('person_name'),
                e.get('image_url'),
                metadata.get('location', ''),
                metadata.get('confidence', 0)
            ])

        output.seek(0)

        filename = f"report_{start_date}_{end_date}.csv"
        response = StreamingResponse(
            iter([output.getvalue().encode('utf-8-sig')]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

        return response

    except Exception as e:
        logger.error(f"导出报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))