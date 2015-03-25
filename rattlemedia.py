from flask import Flask, redirect
from flask_socketio import SocketIO, emit
from config import Config
from gmusicapi import Mobileclient
import logging
import sys

application = Flask(__name__)
application.config['SECRET_KEY'] = Config.secret_key
socket_io = SocketIO(application)


def setup_logging():
    log_formatter = logging.Formatter('[%(asctime)s] %(levelname)s (%(process)d) %(module)s: %(message)s')
    stream_handle = logging.StreamHandler(sys.stdout)
    stream_handle.setLevel(logging.DEBUG)
    stream_handle.setFormatter(log_formatter)
    logger = logging.getLogger('rattlemedia')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stream_handle)

setup_logging()


class RattleMediaController:
    def __init__(self):
        api = Mobileclient()
        api.login(Config.google_username, Config.google_password)
        self.__api = api

        self._logger = logging.getLogger('rattlemedia')

    def search(self, search_term):
        self._logger.debug('Searching for {0}'.format(search_term))
        return self.__api.search_all_access(search_term)

controller = RattleMediaController()

@application.route('/')
def index():
    return redirect('/static/index.html')

@socket_io.on('search')
def search(search_term):
    results = controller.search(search_term)
    print results
    emit('search complete', results)

if __name__ == '__main__':
    socket_io.run(application)