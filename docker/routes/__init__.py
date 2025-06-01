from .songs import songs_bp
from .preview import preview_bp
from .history import history_bp
from .control import control_bp
from .convert import convert_bp

def register_blueprints(app):
    app.register_blueprint(songs_bp)
    app.register_blueprint(preview_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(control_bp)
    app.register_blueprint(convert_bp)
