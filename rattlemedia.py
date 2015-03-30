from flask import Flask, redirect
from flask_socketio import SocketIO, emit
from rattlemediaplayer import RattleMediaController
import config
import logging
import sys

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

controller = RattleMediaController()

@application.route('/')
def index():
    logger.info('Loading home page')
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