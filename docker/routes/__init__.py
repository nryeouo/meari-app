from .songs import songs_bp
from .notify import notify_bp
from .remote import remote_bp
from .preview import preview_bp
from .history import history_bp
from .control import control_bp
from .convert import convert_bp
from .banner import banner_bp

def register_blueprints(app):
    app.register_blueprint(songs_bp)
    app.register_blueprint(notify_bp)
    app.register_blueprint(remote_bp)
    app.register_blueprint(preview_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(control_bp)
    app.register_blueprint(convert_bp)
    app.register_blueprint(banner_bp)
