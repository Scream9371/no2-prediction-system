from flask import Blueprint, render_template, request, send_from_directory
from config.cities import get_city_id
import os

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
    # 从城市名称获取城市ID
    city_id = get_city_id(city_name) if city_name else None
    # 若未找到则默认使用广州ID
    if not city_id:
        city_id = "101280101"  # 默认广州
    # 复用原有的city视图函数逻辑
    return render_template("city.html", city_id=city_id)


# Favicon 路由
@main_bp.route("/favicon.ico")
def favicon():
    # 返回一个简单的响应，避免404错误
    # 实际项目中可以返回真正的favicon文件
    return "", 204
