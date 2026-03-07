import flask
from flask import Flask,send_file
from flaskwebgui import FlaskUI

app = Flask(__name__)

@app.route('/katana/config.json')
def cfgjs():
    return send_file('toup.json')

app.run(debug=True,port=8000)