import datetime

from flask import Blueprint, jsonify

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
    import os
    import json

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
        import os
        from config.paths import get_latest_model_path, get_control_model_path

        # 先尝试训练管道的最新模型
        model_path = get_latest_model_path(city)
        if not os.path.exists(model_path):
            # 如果训练管道模型不存在，尝试控制脚本模型
            model_path = get_control_model_path(city)

        if not os.path.exists(model_path):
            # 如果模型不存在，返回示例数据并提示用户
            import datetime

            current_time = datetime.datetime.now()
            times = [
                (current_time + datetime.timedelta(hours=i)).strftime("%H:%M")
                for i in range(24)
            ]

            # 生成示例预测数据
            import random

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
            import pandas as pd

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
            import datetime

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
            return jsonify({
                "error": f"未找到{city_name}在{yesterday.isoformat()}的历史观测数据",
                "date": yesterday.isoformat(),
                "city": city_name,
                "total_records": 0,
                "suggestion": "请确认数据采集是否正常运行，或稍后重试"
            }), 404

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

        return jsonify({
            "date": yesterday.isoformat(),
            "city": city_name,
            "total_records": len(result),
            "data": result
        })

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
        import os
        import json
        
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
        
        return jsonify({
            "date": yesterday.isoformat(),
            "generated_at": cache_data.get("generated_at"),
            "city": city_name,
            "updateTime": city_predictions.get("updateTime"),
            "times": city_predictions.get("times", []),
            "values": city_predictions.get("values", []),
            "low": city_predictions.get("low", []),
            "high": city_predictions.get("high", [])
        })
        
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
        
        return jsonify({
            "response": ai_response.get("response", ""),
            "isConnected": ai_response.get("isConnected", False),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
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
            structured_questions.append({
                "id": f"preset_{i}",
                "text": question,
                "category": "常见问题"
            })
        
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
        return jsonify({
            "api_configured": False,
            "model_name": "unknown",
            "fallback_available": True,
            "status": "error",
            "error": str(e)
        }), 500


# 在api_routes.py中添加以下路由

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
            return jsonify({
                "error": f"未找到{city_name}在{start_date}至{end_date}的历史观测数据",
                "city": city_name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_records": 0
            }), 404

        # 按日期分组并计算每日平均值
        daily_data = {}
        for record in records:
            # 提取日期部分（忽略时间）
            date_key = record.observation_time.date()

            if date_key not in daily_data:
                daily_data[date_key] = {
                    "sum": 0,
                    "count": 0
                }

            daily_data[date_key]["sum"] += record.no2_concentration
            daily_data[date_key]["count"] += 1

        # 构建返回数据结构
        result_data = []
        for date_key in sorted(daily_data.keys()):
            data = daily_data[date_key]
            result_data.append({
                "date": date_key.isoformat(),
                "avg_no2": round(data["sum"] / data["count"], 1),
                "records": data["count"]
            })

        return jsonify({
            "city": city_name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": result_data
        })

    except Exception as e:
        return jsonify({"error": f"获取历史趋势数据失败: {str(e)}"}), 500


# 在 api_routes.py 中添加以下路由
@api_bp.route("/api/trend/no2/<city_id>")
def get_no2_daily_average(city_id):
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
            return jsonify({
                "error": f"未找到{city_name}在{start_date}至{end_date}的历史观测数据",
                "city": city_name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_records": 0
            }), 404

        # 按日期分组并计算每日平均值
        daily_data = {}
        for record in records:
            # 提取日期部分（忽略时间）
            date_key = record.observation_time.date()

            if date_key not in daily_data:
                daily_data[date_key] = {
                    "sum": 0,
                    "count": 0
                }

            daily_data[date_key]["sum"] += record.no2_concentration
            daily_data[date_key]["count"] += 1

        # 构建返回数据结构
        result_data = []
        for date_key in sorted(daily_data.keys()):
            data = daily_data[date_key]
            result_data.append({
                "date": date_key.isoformat(),
                "avg_no2": round(data["sum"] / data["count"], 1),
                "records": data["count"]
            })

        return jsonify({
            "city": city_name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": result_data
        })

    except Exception as e:
        return jsonify({"error": f"获取历史趋势数据失败: {str(e)}"}), 500