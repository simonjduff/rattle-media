from flask import Flask, redirect
from flask_socketio import SocketIO, emit
import config
from gmusicapi import Mobileclient
import logging
import sys
import gst

application = Flask(__name__)
application.config['SECRET_KEY'] = config.secret_key
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


class MusicPlayer:
    def __init__(self):
        self.queue = []

    def enqueue(self, song_id):
        self.queue.append(song_id)

    def next_track_id(self):
        return self.queue[0]


class RattleMediaController:
    _player = gst.element_factory_make('playbin2', 'player')
    def __init__(self):
        api = Mobileclient()
        api.login(config.google_username, config.google_password)
        self._api = api
        self._logger = logging.getLogger('rattlemedia')
        self._music_player = MusicPlayer()
        RattleMediaController._player.set_state(gst.STATE_NULL)

    def search(self, search_term):
        self._logger.debug('Searching for {0}'.format(search_term))
        return self._api.search_all_access(search_term)

    def enqueue(self, song_id):
        self._music_player.enqueue(song_id)

    def play(self):
        trackUrl = self._api.get_stream_url(self._music_player.next_track_id(), config.google_device_id)
        RattleMediaController._player.set_state(gst.STATE_PLAYING)
        RattleMediaController._player.set_property('uri', trackUrl)

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