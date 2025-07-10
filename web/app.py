from flask import Flask
from web.routes.main_routes import main_bp
from web.routes.api_routes import api_bp

app = Flask(__name__)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    app.run(debug=True)
