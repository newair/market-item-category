# This fill will be executed once the module is configured. It setup the basic configuration
# settings and secret key
from flask import Flask

UPLOAD_FOLDER = 'uploads'

app = Flask(__name__)
app.secret_key = 'super secret key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
