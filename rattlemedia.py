from flask import Flask, redirect
from flask_socketio import SocketIO, emit
from config import Config
from gmusicapi import Mobileclient

application = Flask(__name__)
application.config['SECRET_KEY'] = Config.secret_key
socketio = SocketIO(application)


class RattleMediaController:
    def __init__(self):
        api = Mobileclient()
        api.login(Config.google_username, Config.google_password)
        self.__api = api

    def search(self, searchTerm):
        return self.__api.search_all_access(searchTerm)

controller = RattleMediaController()

@application.route('/')
def index():
    return redirect('/static/index.html')

@socketio.on('search')
def search(search_term):
    results = controller.search(search_term)
    print results
    emit('search complete', results)

if __name__ == '__main__':
    socketio.run(application)