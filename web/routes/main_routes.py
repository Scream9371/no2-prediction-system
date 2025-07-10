from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/city/<city_id>")
def city(city_id):
    return render_template("city.html", city_id=city_id)
