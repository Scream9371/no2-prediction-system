from flask import Blueprint, render_template,request

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/city/<city_id>")
def city(city_id):
    return render_template("city.html", city_id=city_id)

# 新增路由：匹配前端原有的 /city.html?city=xxx 路径
@main_bp.route("/city.html")
def city_html():
    # 获取URL参数中的城市名称
    city_name = request.args.get("city")
    # 从城市名称映射到城市ID（与api_routes.py中的CITY_ID_TO_NAME反向映射）
    city_id_map = {v: k for k, v in {
        "101280101": "广州",
        "101280601": "深圳",
        "101280701": "珠海",
        "101280800": "佛山",
        "101280301": "惠州",
        "101281601": "东莞",
        "101281701": "中山",
        "101281101": "江门",
        "101280901": "肇庆",
        "101320101": "香港特别行政区",
        "101330101": "澳门特别行政区"
    }.items()}
    # 查找对应的城市ID（若未找到则默认使用广州ID）
    city_id = city_id_map.get(city_name, "101280101")
    # 复用原有的city视图函数逻辑
    return render_template("city.html", city_id=city_id)
