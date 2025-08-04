import datetime
import json
import os
import random
import traceback

import pandas as pd
from flask import Blueprint, jsonify, request

from config.cities import get_city_name, is_supported_city, get_all_cities
from database.crud import get_no2_records
from database.session import get_db
from ml.src.predict import predict_for_web_api

# 中文城市名到英文城市名的映射（用于模型文件路径）
CHINESE_TO_ENGLISH_CITY_MAP = {
    "广州": "guangzhou",
    "深圳": "shenzhen",
    "珠海": "zhuhai",
    "佛山": "foshan",
    "惠州": "huizhou",
    "东莞": "dongguan",
    "中山": "zhongshan",
    "江门": "jiangmen",
    "肇庆": "zhaoqing",
    "香港": "hongkong",
    "澳门": "macao",
    # 支持完整的特别行政区名称
    "香港特别行政区": "hongkong",
    "澳门特别行政区": "macao",
}


def get_english_city_name(chinese_name: str) -> str:
    """
    将中文城市名转换为英文城市名（用于模型文件路径）

    Args:
        chinese_name (str): 中文城市名

    Returns:
        str: 英文城市名，如果找不到则返回原名称

    Example:
        >>> get_english_city_name("广州")
        'guangzhou'
        >>> get_english_city_name("未知城市")
        '未知城市'
    """
    return CHINESE_TO_ENGLISH_CITY_MAP.get(chinese_name, chinese_name)


def load_daily_predictions_cache():
    """
    加载每日预测缓存数据

    Returns:
        Dict: 缓存数据，如果不存在返回None
    """

    try:
        cache_dir = os.path.join(os.getcwd(), "data", "predictions_cache")
        cache_file = os.path.join(cache_dir, "latest_predictions.json")

        if not os.path.exists(cache_file):
            return None

        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        return cache_data

    except Exception as e:
        print(f"加载预测缓存失败: {str(e)}")
        return None


def fallback_realtime_prediction(city: str):
    """
    降级到实时预测（当缓存未命中时）

    Args:
        city (str): 城市名称

    Returns:
        JSON响应
    """
    try:
        # 检查模型是否存在
        from config.paths import get_latest_model_path, get_control_model_path

        # 先尝试训练管道的最新模型
        model_path = get_latest_model_path(city)
        if not os.path.exists(model_path):
            # 如果训练管道模型不存在，尝试控制脚本模型
            model_path = get_control_model_path(city)

        if not os.path.exists(model_path):
            # 如果模型不存在，返回示例数据并提示用户

            current_time = datetime.datetime.now()
            times = [
                (current_time + datetime.timedelta(hours=i)).strftime("%H:%M")
                for i in range(24)
            ]

            # 生成示例预测数据

            base_value = random.uniform(30, 80)
            values = [round(base_value + random.uniform(-5, 5), 1) for _ in range(24)]
            low = [round(v - 10, 1) for v in values]
            high = [round(v + 10, 1) for v in values]

            return jsonify(
                {
                    "updateTime": current_time.strftime("%Y-%m-%d %H:%M"),
                    "currentValue": values[0],
                    "avgValue": round(sum(values) / len(values), 1),
                    "times": times,
                    "values": values,
                    "low": low,
                    "high": high,
                    "warning": f"模型文件不存在且缓存未命中，显示示例数据。请先训练模型。",
                    "fallback": True,  # 标记为降级预测
                }
            )

        # 使用实时预测
        predictions_df = predict_for_web_api(city=city, steps=24)

        # 将DataFrame转换为前端需要的JSON格式
        if (
            predictions_df is not None
            and hasattr(predictions_df, "empty")
            and not predictions_df.empty
        ):
            # 从预测数据中提取实际的时间标签

            times = [
                pd.to_datetime(t).strftime("%H:%M")
                for t in predictions_df["observation_time"].tolist()[:24]
            ]

            # 提取预测数据
            values = predictions_df["prediction"].tolist()[:24]
            low = predictions_df["lower_bound"].tolist()[:24]
            high = predictions_df["upper_bound"].tolist()[:24]

            current_value = values[0] if values else 0
            avg_value = sum(values) / len(values) if values else 0

            # 获取当前时间作为更新时间

            current_time = datetime.datetime.now()

            return jsonify(
                {
                    "updateTime": current_time.strftime("%Y-%m-%d %H:%M"),
                    "currentValue": round(current_value, 1),
                    "avgValue": round(avg_value, 1),
                    "times": times,
                    "values": [round(v, 1) for v in values],
                    "low": [round(l, 1) for l in low],
                    "high": [round(h, 1) for h in high],
                    "fallback": True,  # 标记为降级预测
                }
            )
        else:
            return jsonify({"error": "无法获取预测数据，请检查模型和数据"}), 500

    except Exception as e:
        return jsonify({"error": f"降级预测失败: {str(e)}"}), 500


api_bp = Blueprint("api", __name__)


@api_bp.route("/api/no2/<city_id>")
def get_no2(city_id):
    """
    获取指定城市昨天的历史NO₂观测数据

    返回昨天24小时的实际观测数据，用于对比预测数据的准确性。

    Args:
        city_id (str): 城市ID，从URL路径中获取

    Returns:
        JSON: 昨天的历史NO₂数据列表，每条记录包含：
            - observation_time: 观测时间 (ISO格式字符串)
            - no2_concentration: NO₂浓度 (μg/m³)
            - temperature: 气温 (摄氏度)
            - humidity: 相对湿度 (百分比)
            - wind_speed: 风速 (公里/小时)
            - wind_direction: 风向 (360角度)
            - pressure: 大气压 (百帕)

    HTTP状态码:
        200: 成功返回数据
        400: 无效的城市ID
        500: 服务器内部错误

    示例:
        GET /api/no2/101280800
        返回: [{"observation_time": "2025-08-01T00:00:00", "no2_concentration": 25.6, ...}, ...]
    """
    # 转换城市ID为名称
    city_name = get_city_name(city_id)
    if not city_name:
        return jsonify({"error": "无效的城市ID"}), 400

    try:
        from database.crud import CITY_MODEL_MAP

        if city_name not in CITY_MODEL_MAP:
            return jsonify({"error": "不支持的城市"}), 400

        # 计算昨天的日期范围
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        yesterday_start = datetime.datetime.combine(yesterday, datetime.time.min)
        yesterday_end = datetime.datetime.combine(yesterday, datetime.time.max)

        db_gen = get_db()
        db = next(db_gen)

        # 查询昨天的数据
        model_class = CITY_MODEL_MAP[city_name]
        records = (
            db.query(model_class)
            .filter(model_class.observation_time >= yesterday_start)
            .filter(model_class.observation_time <= yesterday_end)
            .order_by(model_class.observation_time.asc())
            .all()
        )
        db.close()

        # 检查是否有数据
        if not records:
            return (
                jsonify(
                    {
                        "error": f"未找到{city_name}在{yesterday.isoformat()}的历史观测数据",
                        "date": yesterday.isoformat(),
                        "city": city_name,
                        "total_records": 0,
                        "suggestion": "请确认数据采集是否正常运行，或稍后重试",
                    }
                ),
                404,
            )

        # 转换记录为字典列表
        result = []
        for record in records:
            record_dict = {}
            for column in record.__table__.columns:
                value = getattr(record, column.name)
                # 处理datetime对象
                if isinstance(value, datetime.datetime):
                    record_dict[column.name] = value.isoformat()
                else:
                    record_dict[column.name] = value
            result.append(record_dict)

        return jsonify(
            {
                "date": yesterday.isoformat(),
                "city": city_name,
                "total_records": len(result),
                "data": result,
            }
        )

    except Exception as e:
        return jsonify({"error": f"获取昨天历史数据失败: {str(e)}"}), 500


@api_bp.route("/api/predict/no2/<city_id>")
def predict_no2(city_id):
    """
    获取指定城市未来24小时的NO₂浓度预测数据

    这是核心预测API，使用训练好的NC-CQR模型预测城市未来24小时的NO₂浓度及95%置信区间。

    Args:
        city_id (str): 城市ID，从URL路径中获取

    Returns:
        JSON: 预测数据，包含以下字段：
            - updateTime (str): 更新时间，格式 "YYYY-MM-DD HH:MM"
            - currentValue (float): 当前预测值 (μg/m³)
            - avgValue (float): 24小时平均预测值 (μg/m³)
            - times (list): 24个时间点，格式 ["HH:MM", ...]，基于实际预测时间
            - values (list): 24个预测值 (μg/m³)
            - low (list): 置信区间下限值 (μg/m³)
            - high (list): 置信区间上限值 (μg/m³)
            - warning (str, 可选): 当模型不存在时的警告信息

    模型选择策略:
        1. 仅使用训练管道的最新模型 (ml/models/latest/)
        2. 模型不存在时返回示例数据并显示警告

    HTTP状态码:
        200: 成功返回预测数据
        400: 不支持的城市ID
        500: 预测过程出错

    示例:
        GET /api/predict/no2/101280800
        返回: {
            "updateTime": "2025-07-25 12:00",
            "currentValue": 25.6,
            "avgValue": 23.4,
            "times": ["00:00", "01:00", ..., "23:00"],
            "values": [25.6, 24.3, ..., 26.8],
            "low": [19.2, 18.1, ..., 20.4],
            "high": [32.0, 30.5, ..., 33.2]
        }
    """
    if not is_supported_city(city_id):
        return jsonify({"error": "不支持的城市"}), 400

    try:
        # 获取城市名称用于预测
        city_name = get_city_name(city_id)
        # 转换为英文城市名（用于模型文件路径）
        english_city_name = get_english_city_name(city_name)

        # 优先从缓存获取预测数据
        cached_data = load_daily_predictions_cache()

        if cached_data and english_city_name in cached_data.get("predictions", {}):
            # 返回缓存的预测数据
            return jsonify(cached_data["predictions"][english_city_name])

        # 缓存未命中，降级到实时预测
        return fallback_realtime_prediction(english_city_name)

    except Exception as e:
        return jsonify({"error": f"预测失败: {str(e)}"}), 500


@api_bp.route("/api/historical-predictions/<city_id>")
def get_historical_predictions(city_id):
    """
    获取指定城市昨天的历史预测数据

    用于预测准确性验证，返回昨天生成的预测数据以便与实际观测数据对比。

    Args:
        city_id (str): 城市ID，从URL路径中获取

    Returns:
        JSON: 昨天的预测数据，包含：
            - date (str): 预测日期 (YYYY-MM-DD)
            - generated_at (str): 预测生成时间
            - updateTime (str): 更新时间
            - times (list): 24个时间点 ["HH:MM", ...]
            - values (list): 24个预测值 (μg/m³)
            - low (list): 置信区间下限 (μg/m³)
            - high (list): 置信区间上限 (μg/m³)

    HTTP状态码:
        200: 成功返回历史预测数据
        400: 无效的城市ID
        404: 未找到昨天的预测数据
        500: 服务器内部错误

    示例:
        GET /api/historical-predictions/101280101
        返回: {
            "date": "2025-08-01",
            "generated_at": "2025-08-01T03:15:22",
            "times": ["00:00", "01:00", ...],
            "values": [25.6, 24.3, ...],
            "low": [19.2, 18.1, ...],
            "high": [32.0, 30.5, ...]
        }
    """
    if not is_supported_city(city_id):
        return jsonify({"error": "不支持的城市"}), 400

    try:
        
        # 获取城市名称并转换为英文
        city_name = get_city_name(city_id)
        english_city_name = get_english_city_name(city_name)

        # 计算昨天的日期
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")

        # 查找昨天的预测缓存文件
        cache_dir = os.path.join(os.getcwd(), "data", "predictions_cache")
        cache_file = os.path.join(cache_dir, f"daily_predictions_{date_str}.json")

        if not os.path.exists(cache_file):
            return jsonify({"error": f"未找到{yesterday}的预测数据"}), 404

        # 读取预测缓存
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        # 检查城市数据是否存在
        predictions = cache_data.get("predictions", {})
        if english_city_name not in predictions:
            return jsonify({"error": f"未找到{city_name}在{yesterday}的预测数据"}), 404

        city_predictions = predictions[english_city_name]

        return jsonify(
            {
                "date": yesterday.isoformat(),
                "generated_at": cache_data.get("generated_at"),
                "city": city_name,
                "updateTime": city_predictions.get("updateTime"),
                "times": city_predictions.get("times", []),
                "values": city_predictions.get("values", []),
                "low": city_predictions.get("low", []),
                "high": city_predictions.get("high", []),
            }
        )

    except Exception as e:
        return jsonify({"error": f"获取历史预测数据失败: {str(e)}"}), 500


@api_bp.route("/api/cities")
def get_cities():
    """
    获取所有支持的城市列表

    返回大湾区所有支持预测的城市信息，包括城市ID和中文名称。
    前端使用此接口获取城市映射关系，用于城市搜索和ID转换。

    Returns:
        JSON: 城市信息列表，每个城市包含：
            - id (str): 城市ID，用于其他API调用
            - name (str): 城市中文名称

    HTTP状态码:
        200: 成功返回城市列表

    示例:
        GET /api/cities
        返回: [
            {"id": "101280101", "name": "广州"},
            {"id": "101280601", "name": "深圳"},
            {"id": "101280800", "name": "佛山"},
            ...
        ]

    支持的城市:
        广州、深圳、珠海、佛山、惠州、东莞、中山、江门、肇庆、香港特别行政区、澳门特别行政区
    """
    return jsonify(get_all_cities())


@api_bp.route("/api/ai-assistant", methods=["POST"])
def ai_assistant():
    """
    AI小助手接口

    处理用户的问题并返回AI回复，支持结合当前城市NO₂数据的上下文回答。

    请求体:
        JSON格式，包含：
        - message (str): 用户问题
        - context (dict): 上下文数据，包含：
            - city (str): 当前城市名称
            - currentValue (float): 当前NO₂浓度值
            - avgValue (float): 24小时平均值
            - qualityLevel (str): 空气质量等级

    Returns:
        JSON: AI回复，包含：
            - response (str): AI回复内容
            - timestamp (str): 回复时间戳

    HTTP状态码:
        200: 成功返回AI回复
        400: 请求参数错误
        500: 服务器内部错误

    示例:
        POST /api/ai-assistant
        请求体: {
            "message": "NO₂的危害有哪些？",
            "context": {
                "city": "广州",
                "currentValue": 25.6,
                "avgValue": 23.4,
                "qualityLevel": "良"
            }
        }
        返回: {
            "response": "NO₂对人体的主要危害包括...",
            "timestamp": "2025-08-03T12:34:56"
        }
    """
    from flask import request

    try:
        # 解析请求数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400

        message = data.get("message", "").strip()
        context = data.get("context", {})

        if not message:
            return jsonify({"error": "消息内容不能为空"}), 400

        # 调用AI处理函数
        from api.ai_service import ai_service

        ai_response = ai_service.process_request(message, context)

        return jsonify(
            {
                "response": ai_response.get("response", ""),
                "isConnected": ai_response.get("isConnected", False),
                "timestamp": datetime.datetime.now().isoformat(),
            }
        )

    except Exception as e:

        print(f"AI助手请求处理失败: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"AI助手服务暂时不可用: {str(e)}"}), 500


@api_bp.route("/api/ai-assistant/preset-questions")
def get_preset_questions():
    """
    获取AI助手预设问题列表

    返回NO₂相关的常见问题列表，用于前端快速问答功能。

    Returns:
        JSON: 预设问题列表
            - questions (list): 问题列表，每个问题包含：
                - id (str): 问题ID
                - text (str): 问题文本
                - category (str): 问题分类

    HTTP状态码:
        200: 成功返回预设问题列表

    示例:
        GET /api/ai-assistant/preset-questions
        返回: {
            "questions": [
                {
                    "id": "no2_harm",
                    "text": "NO₂的危害有哪些？",
                    "category": "基础知识"
                },
                ...
            ]
        }
    """
    try:
        from api.ai_service import get_preset_questions

        questions = get_preset_questions()

        # 将问题转换为结构化格式
        structured_questions = []
        for i, question in enumerate(questions):
            structured_questions.append(
                {"id": f"preset_{i}", "text": question, "category": "常见问题"}
            )

        return jsonify({"questions": structured_questions})

    except Exception as e:
        return jsonify({"error": f"获取预设问题失败: {str(e)}"}), 500


@api_bp.route("/api/ai-assistant/config")
def get_ai_config():
    """
    获取AI助手配置信息

    返回AI服务的配置状态，用于前端判断功能可用性。

    Returns:
        JSON: AI配置信息
            - api_configured (bool): API是否已配置
            - model_name (str): 使用的模型名称
            - fallback_available (bool): 降级服务是否可用
            - status (str): 服务状态

    HTTP状态码:
        200: 成功返回配置信息

    示例:
        GET /api/ai-assistant/config
        返回: {
            "api_configured": true,
            "model_name": "gpt-3.5-turbo",
            "fallback_available": true,
            "status": "ready"
        }
    """
    try:
        from api.ai_service import validate_ai_config

        config = validate_ai_config()

        # 添加服务状态
        if config["api_key_configured"]:
            config["status"] = "ready"
        elif config["fallback_available"]:
            config["status"] = "fallback"
        else:
            config["status"] = "unavailable"

        return jsonify(config)

    except Exception as e:
        return (
            jsonify(
                {
                    "api_configured": False,
                    "model_name": "unknown",
                    "fallback_available": True,
                    "status": "error",
                    "error": str(e),
                }
            ),
            500,
        )


@api_bp.route("/api/trend/no2/<city_id>")
def get_no2_trend(city_id):
    """
    获取指定城市过去15天（不包含今天）的每日平均NO₂浓度数据

    用于前端展示近15天浓度趋势图

    Args:
        city_id (str): 城市ID

    Returns:
        JSON: 包含以下字段：
            - city: 城市名称
            - start_date: 开始日期 (YYYY-MM-DD)
            - end_date: 结束日期 (YYYY-MM-DD)
            - data: 数据列表，每个元素包含：
                - date: 日期 (YYYY-MM-DD)
                - avg_no2: 当日平均NO₂浓度 (μg/m³)
                - records: 当日数据记录条数

    HTTP状态码:
        200: 成功返回数据
        400: 无效的城市ID
        404: 无数据
        500: 服务器内部错误
    """
    # 转换城市ID为名称
    city_name = get_city_name(city_id)
    if not city_name:
        return jsonify({"error": "无效的城市ID"}), 400

    try:
        from database.crud import CITY_MODEL_MAP

        if city_name not in CITY_MODEL_MAP:
            return jsonify({"error": "不支持的城市"}), 400

        # 计算日期范围：过去15天（不包含今天）
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=15)
        end_date = today - datetime.timedelta(days=1)  # 昨天

        db_gen = get_db()
        db = next(db_gen)
        model_class = CITY_MODEL_MAP[city_name]

        # 查询15天内的数据
        records = (
            db.query(model_class)
            .filter(model_class.observation_time >= start_date)
            .filter(model_class.observation_time < today)  # 不包含今天
            .order_by(model_class.observation_time.asc())
            .all()
        )
        db.close()

        if not records:
            return (
                jsonify(
                    {
                        "error": f"未找到{city_name}在{start_date}至{end_date}的历史观测数据",
                        "city": city_name,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "total_records": 0,
                    }
                ),
                404,
            )

        # 按日期分组并计算每日平均值
        daily_data = {}
        for record in records:
            # 提取日期部分（忽略时间）
            date_key = record.observation_time.date()

            if date_key not in daily_data:
                daily_data[date_key] = {"sum": 0, "count": 0}

            daily_data[date_key]["sum"] += record.no2_concentration
            daily_data[date_key]["count"] += 1

        # 构建返回数据结构
        result_data = []
        for date_key in sorted(daily_data.keys()):
            data = daily_data[date_key]
            result_data.append(
                {
                    "date": date_key.isoformat(),
                    "avg_no2": round(data["sum"] / data["count"], 1),
                    "records": data["count"],
                }
            )

        return jsonify(
            {
                "city": city_name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": result_data,
            }
        )

    except Exception as e:
        return jsonify({"error": f"获取历史趋势数据失败: {str(e)}"}), 500


@api_bp.route("/api/trend/analysis/<city_id>")
def get_trend_analysis(city_id):
    """
    获取指定城市近15天NO₂浓度的AI智能分析报告
    
    通过大模型分析历史数据，生成包含以下内容的专业报告：
    - 整体趋势分析
    - 周期性变化分析
    - 异常值检测
    - 环境因素影响评估
    
    缓存策略：
    - 每个城市每天只生成一次分析报告
    - 缓存有效期到当天午夜自动失效
    
    Args:
        city_id (str): 城市ID
        
    Returns:
        JSON: 包含AI分析报告的响应：
            - city: 城市名称
            - analysis_date: 分析日期
            - overall_trend: 整体趋势分析
            - periodic_changes: 周期性变化分析
            - anomaly_detection: 异常值检测
            - environmental_factors: 环境因素影响评估
            - summary: 总结建议
            - generated_at: 生成时间
            - cached: 是否来自缓存
    """
    # 转换城市ID为名称
    city_name = get_city_name(city_id)
    if not city_name:
        return jsonify({"error": "无效的城市ID"}), 400

    # 检查是否强制刷新
    force_refresh = request.args.get('refresh', '').lower() == 'true'
    
    # 检查缓存
    today = datetime.date.today().isoformat()
    cache_key = f"trend_analysis_{city_name}_{today}"
    
    # 简单的内存缓存检查
    cache_dir = "data/cache/trend_analysis"
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    
    # 确保缓存目录存在
    os.makedirs(cache_dir, exist_ok=True)
    
    # 检查今日缓存是否存在且有效（除非强制刷新）
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_result = json.load(f)
            
            # 检查缓存是否是今天生成的
            if cached_result.get("analysis_date") == today:
                cached_result["cached"] = True
                return jsonify(cached_result)
        except Exception as e:
            print(f"读取缓存失败: {str(e)}")
            # 缓存损坏，删除文件
            try:
                os.remove(cache_file)
            except:
                pass

    try:
        from database.crud import CITY_MODEL_MAP
        
        if city_name not in CITY_MODEL_MAP:
            return jsonify({"error": "不支持的城市"}), 400

        # 获取近15天的数据
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=15)
        end_date = today - datetime.timedelta(days=1)

        db_gen = get_db()
        db = next(db_gen)
        model_class = CITY_MODEL_MAP[city_name]

        # 查询15天内的数据
        records = (
            db.query(model_class)
            .filter(model_class.observation_time >= start_date)
            .filter(model_class.observation_time < today)
            .order_by(model_class.observation_time.asc())
            .all()
        )
        db.close()

        if not records:
            return jsonify({
                "error": f"未找到{city_name}在{start_date}至{end_date}的历史数据",
                "city": city_name
            }), 404

        # 处理数据：按日期分组并计算统计信息
        daily_data = {}
        all_values = []
        hourly_data = {}  # 按小时统计，用于周期性分析
        
        for record in records:
            date_key = record.observation_time.date()
            hour_key = record.observation_time.hour
            concentration = record.no2_concentration
            
            # 日数据统计
            if date_key not in daily_data:
                daily_data[date_key] = {
                    "values": [],
                    "temperature": [],
                    "humidity": [],
                    "wind_speed": []
                }
            
            daily_data[date_key]["values"].append(concentration)
            daily_data[date_key]["temperature"].append(record.temperature)
            daily_data[date_key]["humidity"].append(record.humidity)
            daily_data[date_key]["wind_speed"].append(record.wind_speed)
            
            # 小时数据统计
            if hour_key not in hourly_data:
                hourly_data[hour_key] = []
            hourly_data[hour_key].append(concentration)
            
            all_values.append(concentration)

        # 计算每日统计数据
        trend_data = []
        for date_key in sorted(daily_data.keys()):
            data = daily_data[date_key]
            trend_data.append({
                "date": date_key.isoformat(),
                "avg_no2": round(sum(data["values"]) / len(data["values"]), 1),
                "max_no2": round(max(data["values"]), 1),
                "min_no2": round(min(data["values"]), 1),
                "avg_temp": round(sum(data["temperature"]) / len(data["temperature"]), 1),
                "avg_humidity": round(sum(data["humidity"]) / len(data["humidity"]), 1),
                "avg_wind": round(sum(data["wind_speed"]) / len(data["wind_speed"]), 1),
                "count": len(data["values"])
            })

        # 调用AI分析服务
        from api.ai_service import ai_service
        
        # 构建分析上下文
        analysis_context = {
            "city": city_name,
            "analysis_period": f"{start_date.isoformat()} 至 {end_date.isoformat()}",
            "data_summary": {
                "total_days": len(trend_data),
                "avg_concentration": round(sum(all_values) / len(all_values), 1),
                "max_concentration": round(max(all_values), 1),
                "min_concentration": round(min(all_values), 1),
                "std_deviation": round((sum([(x - sum(all_values)/len(all_values))**2 for x in all_values]) / len(all_values))**0.5, 2)
            },
            "daily_trends": trend_data[:7],  # 只传最近7天的详细数据
            "hourly_patterns": {
                hour: round(sum(values) / len(values), 1) 
                for hour, values in hourly_data.items()
            }
        }
        
        # 生成AI分析报告
        analysis_prompt = f"""请作为环境数据分析专家，对{city_name}近15天的NO₂浓度数据进行深度分析。

数据概况：
- 分析期间：{analysis_context['analysis_period']}
- 总天数：{analysis_context['data_summary']['total_days']}天
- 平均浓度：{analysis_context['data_summary']['avg_concentration']}μg/m³
- 浓度范围：{analysis_context['data_summary']['min_concentration']} - {analysis_context['data_summary']['max_concentration']}μg/m³
- 标准差：{analysis_context['data_summary']['std_deviation']}

请提供以下四个方面的专业分析（每个方面2-3句话）：

1. 整体趋势分析：
2. 周期性变化分析：
3. 异常值检测：
4. 环境因素影响评估：

最后提供一句总结建议。"""

        ai_response = ai_service.process_request(analysis_prompt, analysis_context)
        
        # 生成基础统计分析作为降级回答
        basic_analysis = generate_basic_trend_analysis(trend_data, analysis_context)
        
        if ai_response.get("isConnected", False):
            # AI连接成功，解析分析结果
            analysis_text = ai_response.get("response", "")
            print(f"AI原始回复: {analysis_text}")  # 调试日志
            
            # 尝试解析AI回复
            try:
                analysis_result = parse_ai_analysis_response(analysis_text)
                
                # 检查解析结果，如果有空字段则用降级回答补充
                for key in analysis_result:
                    if not analysis_result[key]:
                        analysis_result[key] = basic_analysis.get(key, "暂无该项分析")
                        
                # 标记为AI生成（即使部分使用了降级）
                ai_generated = True
                
            except Exception as e:
                print(f"AI回复解析失败，使用降级分析: {str(e)}")
                analysis_result = basic_analysis
                ai_generated = False
                
        else:
            # AI不可用，使用基础统计分析
            print("AI服务不可用，使用降级分析")
            analysis_result = basic_analysis
            ai_generated = False

        # 构建返回结果
        result = {
            "city": city_name,
            "analysis_date": datetime.date.today().isoformat(),
            "data_period": f"{start_date.isoformat()} 至 {end_date.isoformat()}",
            "overall_trend": analysis_result.get("overall_trend", "暂无分析结果"),
            "periodic_changes": analysis_result.get("periodic_changes", "暂无分析结果"),
            "anomaly_detection": analysis_result.get("anomaly_detection", "暂无分析结果"),
            "environmental_factors": analysis_result.get("environmental_factors", "暂无分析结果"),
            "summary": analysis_result.get("summary", "暂无分析结果"),
            "generated_at": datetime.datetime.now().isoformat(),
            "ai_generated": ai_generated,
            "cached": False
        }
        
        # 保存到缓存
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"分析结果已缓存到: {cache_file}")
        except Exception as e:
            print(f"保存缓存失败: {str(e)}")
        
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"生成趋势分析失败: {str(e)}"}), 500


def parse_ai_analysis_response(ai_text):
    """解析AI分析回复，提取四个分析部分"""
    
    # 初始化结果字典
    result = {
        "overall_trend": "",
        "periodic_changes": "",
        "anomaly_detection": "",
        "environmental_factors": "",
        "summary": ""
    }
    
    try:
        # 按行分割文本
        lines = ai_text.strip().split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检测各个分析部分的开始
            if "整体趋势分析" in line or "1." in line and "整体趋势" in line:
                if current_section and current_content:
                    result[current_section] = ' '.join(current_content)
                current_section = "overall_trend"
                current_content = []
                # 提取冒号后的内容
                if "：" in line:
                    content = line.split("：", 1)[1].strip()
                    if content:
                        current_content.append(content)
                        
            elif "周期性变化分析" in line or "2." in line and "周期性" in line:
                if current_section and current_content:
                    result[current_section] = ' '.join(current_content)
                current_section = "periodic_changes"
                current_content = []
                if "：" in line:
                    content = line.split("：", 1)[1].strip()
                    if content:
                        current_content.append(content)
                        
            elif "异常值检测" in line or "3." in line and "异常" in line:
                if current_section and current_content:
                    result[current_section] = ' '.join(current_content)
                current_section = "anomaly_detection"
                current_content = []
                if "：" in line:
                    content = line.split("：", 1)[1].strip()
                    if content:
                        current_content.append(content)
                        
            elif "环境因素" in line or "4." in line and "环境" in line:
                if current_section and current_content:
                    result[current_section] = ' '.join(current_content)
                current_section = "environmental_factors"
                current_content = []
                if "：" in line:
                    content = line.split("：", 1)[1].strip()
                    if content:
                        current_content.append(content)
                        
            elif "总结" in line or "建议" in line:
                if current_section and current_content:
                    result[current_section] = ' '.join(current_content)
                current_section = "summary"
                current_content = []
                if "：" in line:
                    content = line.split("：", 1)[1].strip()
                    if content:
                        current_content.append(content)
                        
            elif current_section and line:
                # 继续添加到当前部分
                current_content.append(line)
        
        # 处理最后一个部分
        if current_section and current_content:
            result[current_section] = ' '.join(current_content)
        
        # 如果某些部分为空，尝试从整体文本中提取
        if not any(result.values()):
            # 简单处理：将整个回复分配给整体趋势分析
            sentences = ai_text.split('。')
            if len(sentences) >= 4:
                result["overall_trend"] = sentences[0] + '。'
                result["periodic_changes"] = sentences[1] + '。' if len(sentences) > 1 else ""
                result["anomaly_detection"] = sentences[2] + '。' if len(sentences) > 2 else ""
                result["environmental_factors"] = sentences[3] + '。' if len(sentences) > 3 else ""
                result["summary"] = sentences[-1] if sentences[-1] else "数据分析完成。"
            else:
                result["overall_trend"] = ai_text[:100] + "..." if len(ai_text) > 100 else ai_text
                result["summary"] = "AI分析完成，请参考具体内容。"
        
        # 不再使用无意义占位符，保持字段为空由上层处理
                
    except Exception as e:
        print(f"解析AI回复失败: {str(e)}")
        # 返回空结果，由上层使用降级分析
        raise e
    
    return result


def generate_basic_trend_analysis(trend_data, context):
    """当AI不可用时的基础趋势分析"""
    
    if len(trend_data) < 2:
        return {
            "overall_trend": "数据不足，无法进行趋势分析。",
            "periodic_changes": "需要更多数据进行周期性分析。",
            "anomaly_detection": "数据量不足以检测异常值。",
            "environmental_factors": "无法评估环境因素影响。",
            "summary": "建议积累更多历史数据后再进行分析。"
        }
    
    # 简单的趋势计算
    first_week = trend_data[:7]
    last_week = trend_data[-7:]
    first_avg = sum([d["avg_no2"] for d in first_week]) / len(first_week)
    last_avg = sum([d["avg_no2"] for d in last_week]) / len(last_week)
    
    trend_direction = "上升" if last_avg > first_avg else "下降" if last_avg < first_avg else "稳定"
    change_percent = abs((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
    
    # 检测异常值
    all_values = [d["avg_no2"] for d in trend_data]
    avg_val = sum(all_values) / len(all_values)
    std_val = (sum([(x - avg_val)**2 for x in all_values]) / len(all_values))**0.5
    anomalies = [d for d in trend_data if abs(d["avg_no2"] - avg_val) > 2 * std_val]
    
    return {
        "overall_trend": f"近15天NO₂浓度总体呈{trend_direction}趋势，变化幅度约{change_percent:.1f}%。平均浓度{context['data_summary']['avg_concentration']}μg/m³。",
        "periodic_changes": f"工作日与周末浓度存在差异，日间变化相对规律。浓度波动范围{context['data_summary']['min_concentration']}-{context['data_summary']['max_concentration']}μg/m³。",
        "anomaly_detection": f"检测到{len(anomalies)}天异常值，主要集中在浓度超过{avg_val + 2*std_val:.1f}μg/m³的时段。" if anomalies else "未检测到明显异常值，数据变化相对稳定。",
        "environmental_factors": "气象条件对浓度变化有一定影响，风速增强时浓度相对较低，静稳天气下容易accumulate。",
        "summary": f"总体来看，{context['city']}近期空气质量{trend_direction}，建议持续关注变化趋势。"
    }
