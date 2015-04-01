import config
from gmusicapi import Mobileclient
import logging
from gi.repository import Gst, GLib
from collections import deque
from gevent import Greenlet
import gevent


class PlayerStates:
    Stopped = 0
    Paused = 1
    Playing = 2


class RattleMediaPlayer:
    def __init__(self, controller):
        self._logger = logging.getLogger('rattlemedia')
        self._controller = controller
        Gst.init(None)
        self._player = Gst.ElementFactory.make('playbin', None)
        if not self._player:
            raise Exception('Player is None')

        self.set_state(PlayerStates.Stopped)

        self._logger.info('Starting to watch for gstreamer signals')
        Greenlet.spawn(self.watch_for_message)

    def watch_for_message(self):
        bus = self._player.get_bus()

        if not bus:
            raise Exception('Couldn\'t create bus')
        # Ideally we'd be using signal_watch on bus to fire on an event basis
        # but getting the GLib main loop to work with gevent has proved problematic
        # Polling works, but isn't as elegant
        while True:
            message = bus.pop()
            if message:
                self._logger.debug('Message received: {0}'.format(message.type))
                if message.type == Gst.MessageType.EOS:
                    self._logger.info('End of stream received')
                    self._controller.end_of_stream_event()
                elif message.type == Gst.MessageType.STATE_CHANGED:
                    self._logger.debug('State changed {0}'.format(self._player.get_state(100)[1]))

            if not message:
                gevent.sleep(0.5)

    def set_state(self, state):
        if state == PlayerStates.Stopped:
            self._player.set_state(Gst.State.NULL)
        elif state == PlayerStates.Paused:
            self._player.set_state(Gst.State.PAUSED)
        elif state == PlayerStates.Playing:
            self._player.set_state(Gst.State.PLAYING)
        else:
            raise Exception('Unknown state')

    def get_state(self):
        current_state = self._player.get_state(Gst.CLOCK_TIME_NONE)[1]
        if current_state == Gst.State.NULL:
            return PlayerStates.Stopped
        elif current_state == Gst.State.PAUSED:
            return PlayerStates.Paused
        elif current_state == Gst.State.PLAYING:
            return PlayerStates.Playing
        else:
            self._logger.error('GStreamer player in unknown state {0}'.format(current_state))

    def play_track(self, track_url):
            self._player.set_property('uri', track_url)
            self._player.set_state(Gst.State.PLAYING)

    def stop(self):
        self.set_state(PlayerStates.Stopped)

    def pause(self):
        self.set_state(PlayerStates.Paused)


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
            self._player.play_track(track_url)
        except IndexError:
            self._logger.info('Queue empty. Stopping.')
            self._player.set_state(PlayerStates.Stopped)
        finally:
            self._controller.update_state()

    def stop(self):
        self._logger.info('Stopping')
        self._player.set_state(PlayerStates.Stopped)
        self._controller.update_state()

    def toggle(self):
        pass


class PlayerStatePlaying(PlayerState):
    def play(self):
        pass

    def toggle(self):
        self._player.set_state(PlayerStates.Paused)
        self._controller.update_state()


class PlayerStateStopped(PlayerState):
    def stop(self):
        pass

    def toggle(self):
        pass


class PlayerStatePaused(PlayerState):
    def play(self):
        self._player.set_state(PlayerStates.Playing)
        self._controller.update_state()

    def toggle(self):
        self.play()


class RattleMediaController:
    _states = None

    def __init__(self):
        api = Mobileclient()
        api.login(config.google_username, config.google_password)
        self._api = api
        self._logger = logging.getLogger('rattlemedia')

        self._player = RattleMediaPlayer(self)

        self._queue = deque([])

        RattleMediaController._states = {PlayerStates.Paused: PlayerStatePaused(self, self._player),
                                         PlayerStates.Stopped: PlayerStateStopped(self, self._player),
                                         PlayerStates.Playing: PlayerStatePlaying(self, self._player),
                                         'Unknown': PlayerState(self, self._player)}

        self.state = PlayerState(self, self._player)
        self.update_state()

    def end_of_stream_event(self):
        self._player.set_state(PlayerStates.Stopped)
        self.update_state()
        self.play()

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
        self._queue.clear()
        self.enqueue_album(album_id)
        self.play()

    def enqueue_album(self, album_id):
        album = self._api.get_album_info(album_id)
        tracks = album['tracks']
        for track in tracks:
            self._queue.append(track['nid'])

    def update_state(self):
        try:
            logger = logging.getLogger('rattlemedia')
            current_state = self._player.get_state()
            logger.debug('Switching state to {0}'.format(current_state))
            self.state = self._states[current_state]
            logger.info('Switched state to {0}'.format(self.state))
        except KeyError:
            logger.warn('Switching to unknown state {0}'.format(current_state))
            self.state = self._states['Unknown']

