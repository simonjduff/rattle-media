import config
from gmusicapi import Mobileclient
import logging
from gi.repository import Gst, GLib
from collections import deque
from gevent import Greenlet
import gevent


class PlayerState:
    def __init__(self, controller, player):
        self._player = player
        self._controller = controller
        self._logger = logging.getLogger('rattlemedia')

    def play(self):
        self._logger.info('Playing')
        try:
            # This sucks a bit. Should state own the api?
            track_url = self._controller._api.get_stream_url(self._controller._queue.popleft(), config.google_device_id)
            self._player.set_property('uri', track_url)
            self._player.set_state(Gst.State.PLAYING)
        except IndexError:
            self._logger.info('Queue empty. Stopping.')
            self._player.set_state(Gst.State.NULL)
        finally:
            self._controller.update_state()

    def stop(self):
        self._logger.info('Stopping')
        self._player.set_state(Gst.State.NULL)
        self._controller.update_state()

    def toggle(self):
        pass


class PlayerStatePlaying(PlayerState):
    def play(self):
        pass

    def toggle(self):
        self._player.set_state(Gst.State.PAUSED)
        self._controller.update_state()


class PlayerStateStopped(PlayerState):
    def stop(self):
        pass

    def toggle(self):
        pass


class PlayerStatePaused(PlayerState):
    def play(self):
        self._player.set_state(Gst.State.PLAYING)
        self._controller.update_state()

    def toggle(self):
        self.play()


class RattleMediaController:
    _player = None
    _states = None

    def __init__(self):
        Gst.init(None)
        RattleMediaController._player = Gst.ElementFactory.make('playbin', None)

        if not RattleMediaController._player:
            raise Exception('Player is None')

        api = Mobileclient()
        api.login(config.google_username, config.google_password)
        self._api = api
        self._logger = logging.getLogger('rattlemedia')
        RattleMediaController._player.set_state(Gst.State.NULL)

        self._logger.info('Starting to watch for gstreamer signals')
        Greenlet.spawn(RattleMediaController.watch_for_message, self)

        self._queue = deque([])

        RattleMediaController._states = {Gst.State.PAUSED: PlayerStatePaused(self, RattleMediaController._player),
                                         Gst.State.NULL: PlayerStateStopped(self, RattleMediaController._player),
                                         Gst.State.PLAYING: PlayerStatePlaying(self, RattleMediaController._player),
                                         'Unknown': PlayerState(self, RattleMediaController._player)}

        self.state = PlayerState(self, RattleMediaController._player)
        self.update_state()

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
                elif message.type == Gst.MessageType.STATE_CHANGED:
                    logger.debug('State changed {0}'.format(media_player._player.get_state(100)[1]))

            if not message:
                gevent.sleep(0.5)

    def search(self, search_term):
        self._logger.debug('Searching for {0}'.format(search_term))
        return self._api.search_all_access(search_term)

    def enqueue(self, song_id):
        self._logger.info('Enqueuing {0}'.format(song_id))
        self._queue.append(song_id)

    def play(self):
        self.state.play()

    def stop(self):
        self.state.stop()

    def toggle_playback(self):
        self.state.toggle()

    def play_album(self, album_id):
        self._logger.info('Playing album {0}'.format(album_id))
        self.stop()
        album = self._api.get_album_info(album_id)
        tracks = album['tracks']
        self._queue.clear()
        for track in tracks:
            self._queue.append(track['nid'])
        self.play()

    def update_state(self):
        try:
            logger = logging.getLogger('rattlemedia')
            current_state = RattleMediaController._player.get_state(Gst.CLOCK_TIME_NONE)[1]
            logger.info('Switching state to {0}'.format(current_state))
            logger.debug('My states: {0} {1} equal? {2}'.format(current_state,
                                                                      Gst.State.PLAYING,
                                                                      current_state == Gst.State.PLAYING))
            self.state = RattleMediaController._states[current_state]
            logger.info('Switched state to {0}'.format(self.state))
        except KeyError:
            logger.warn('Switching to unknown state {0}'.format(current_state))
            self.state = RattleMediaController._states['Unknown']

