from flask import Flask, redirect
from flask_socketio import SocketIO, emit

application = Flask(__name__)
application.config['SECRET_KEY'] = 'secret!' # Really not sure what this does
socketio = SocketIO(application)

@application.route('/')
def index():
    return redirect('/static/index.html')

@socketio.on('my event')
def test_message(message):
    emit('my response', {'data': 'got it!'})

if __name__ == '__main__':
    socketio.run(application)