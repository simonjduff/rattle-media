from flask import Flask, redirect
from flask_socketio import SocketIO, emit
import config
from gmusicapi import Mobileclient
import logging
import sys
import gst
from collections import deque

application = Flask(__name__)
application.config['SECRET_KEY'] = config.secret_key
socket_io = SocketIO(application)

logger = None

def setup_logging():
    global logger
    log_formatter = logging.Formatter('[%(asctime)s] %(levelname)s (%(process)d) %(module)s: %(message)s')
    stream_handle = logging.StreamHandler(sys.stdout)
    stream_handle.setLevel(logging.DEBUG)
    stream_handle.setFormatter(log_formatter)
    logger = logging.getLogger('rattlemedia')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stream_handle)

setup_logging()


class EmptySongQueue(Exception):
    pass


class MusicPlayer:
    def __init__(self):
        self.queue = deque([])

    def enqueue(self, song_id):
        self.queue.append(song_id)

    def dequeue(self):
        try:
            return self.queue.popleft()
        except IndexError:
            raise EmptySongQueue

    def clear(self):
        self.queue.clear()


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
        try:
            track_url = self._api.get_stream_url(self._music_player.dequeue(), config.google_device_id)
            RattleMediaController._player.set_property('uri', track_url)
            RattleMediaController._player.set_state(gst.STATE_PLAYING)
        except EmptySongQueue:
            pass

    def stop(self):
        self._player.set_state(gst.STATE_NULL)

    def toggle_playback(self):
        self._player.set_state(gst.STATE_PAUSED)

    def play_album(self, album_id):
        self.stop()
        album = self._api.get_album_info(album_id)
        tracks = album['tracks']
        self._music_player.clear()
        for track in tracks:
            self._music_player.enqueue(track['nid'])
        self.play()


controller = RattleMediaController()

@application.route('/')
def index():
    logger.info('starting')
    return redirect('/static/index.html')

@socket_io.on('search')
def search(search_term):
    results = controller.search(search_term)
    print results
    emit('search complete', results)

# This isn't quite right as an API. Play should probably clear the queue then play the specified song.
@socket_io.on('play song')
def play_song(song_id):
    logger.info('Playing song {0}'.format(song_id))
    controller.enqueue(song_id)
    controller.play()

@socket_io.on('stop')
def stop(message):
    logger.info('stopping')
    controller.stop()

@socket_io.on('toggle playback')
def toggle_playback(message):
    logger.info('toggling')
    controller.toggle_playback()

@socket_io.on('play album')
def play_album(album_id):
    logger.info('playing album {0}'.format(album_id))
    controller.play_album(album_id)

if __name__ == '__main__':
    socket_io.run(application)