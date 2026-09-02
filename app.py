"""DocDiff — Document similarity comparison tool (v1.1).

Entry point: creates Flask app, registers routes, starts server.
Debug mode is controlled by FLASK_DEBUG environment variable (default: off).
"""

from flask import Flask, jsonify

from src.config import config
from src.routes import bp
from src.services import ensure_upload_folder

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.max_content_length
app.config['UPLOAD_FOLDER'] = config.upload_folder

app.register_blueprint(bp)


@app.errorhandler(413)
def too_large(_e):
    return jsonify({'error': True, 'code': 'FILE_TOO_LARGE', 'message': 'File exceeds size limit'}), 413


if __name__ == '__main__':
    ensure_upload_folder()
    app.run(
        debug=config.flask_debug,
        host=config.host,
        port=config.port,
    )
