import config
from gmusicapi import Mobileclient
import logging
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from collections import deque
from gevent import Greenlet
import gevent


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
    _player = None

    def __init__(self):
        Gst.init(None)
        RattleMediaController._player = Gst.ElementFactory.make('playbin', None)

        if not RattleMediaController._player:
            raise Exception('Player is None')

        api = Mobileclient()
        api.login(config.google_username, config.google_password)
        self._api = api
        self._logger = logging.getLogger('rattlemedia')
        self._music_player = MusicPlayer()
        RattleMediaController._player.set_state(Gst.State.NULL)

        self._logger.info('Starting to watch for gstreamer signals')
        Greenlet.spawn(RattleMediaController.watch_for_message, self)

    @staticmethod
    def watch_for_message(media_player):
        bus = RattleMediaController._player.get_bus()
        logger = logging.getLogger('rattlemedia')
        if not bus:
            raise Exception('Couldn\'t create bus')
        # Ideally we'd be using signal_watch on bus to fire on an event basis
        # but getting the GLib main loop to work with gevent has proved problematic
        # Polling works, but isn't as elegant
        while True:
            message = bus.pop()
            if message:
                logger.debug('Message received: {0}'.format(message.type))
                if message.type == Gst.MessageType.EOS:
                    logger.info('End of stream received')
                    RattleMediaController._player.set_state(Gst.State.NULL)
                    media_player.play()

            if not message:
                gevent.sleep(0.5)

    def search(self, search_term):
        self._logger.debug('Searching for {0}'.format(search_term))
        return self._api.search_all_access(search_term)

    def enqueue(self, song_id):
        self._logger.info('Enqueuing {0}'.format(song_id))
        self._music_player.enqueue(song_id)

    def play(self):
        self._logger.info('Playing')
        try:
            track_url = self._api.get_stream_url(self._music_player.dequeue(), config.google_device_id)
            RattleMediaController._player.set_property('uri', track_url)
            RattleMediaController._player.set_state(Gst.State.PLAYING)
        except EmptySongQueue:
            pass

    def stop(self):
        self._logger.info('Stopping')
        self._player.set_state(Gst.State.NULL)

    def toggle_playback(self):
        self._logger.info('Toggling')
        self._player.set_state(Gst.State.PAUSED)

    def play_album(self, album_id):
        self._logger.info('Playing album {0}'.format(album_id))
        self.stop()
        album = self._api.get_album_info(album_id)
        tracks = album['tracks']
        self._music_player.clear()
        for track in tracks:
            self._music_player.enqueue(track['nid'])
        self.play()