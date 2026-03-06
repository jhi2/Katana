import flask
from flask import *
from version import *
from configmanager import *
app = Flask(__name__)
config = ConfigManager()
@app.route('/')
def load():
    if config.check_config("config.json"):
        return render_template('index.html', version=v, page_title="Katana")
    else:
        return render_template('welcomeflow.html', version=v, page_title="Katana")

@app.route('/welcome')
def welcome():
    return render_template('welcomeflow.html', version=v, page_title="Katana")
