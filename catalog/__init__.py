from flask import Flask

UPLOAD_FOLDER = 'uploads'

app = Flask(__name__)
app.secret_key = 'super secret key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
