import config
from gmusicapi import Mobileclient
import logging
from gi.repository import Gst, GLib
from collections import deque
from gevent import Greenlet
import gevent


class PlayerStates:
    Stopped = "Stopped"
    Paused = "Paused"
    Playing = "Playing"


class RattleMediaPlayer:
    def __init__(self):
        self._logger = logging.getLogger('rattlemedia')
        Gst.init(None)
        self._player = Gst.ElementFactory.make('playbin', None)
        if not self._player:
            raise Exception('Player is None')

        self._player.set_state(Gst.State.NULL)

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
                    self.end_of_stream_event_handler()
                elif message.type == Gst.MessageType.STATE_CHANGED:
                    self._logger.debug('State changed {0}'.format(self._player.get_state(100)[1]))

            if not message:
                gevent.sleep(0.5)

    def _set_state(self, state):
        try:
            if state == PlayerStates.Stopped:
                self._player.set_state(Gst.State.NULL)
            elif state == PlayerStates.Paused:
                self._player.set_state(Gst.State.PAUSED)
            elif state == PlayerStates.Playing:
                self._player.set_state(Gst.State.PLAYING)
            else:
                raise Exception('Unknown state')
        finally:
            self.state_change_event_handler()

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
            self._set_state(PlayerStates.Playing)

    def stop(self):
        self._set_state(PlayerStates.Stopped)

    def pause(self):
        self._set_state(PlayerStates.Paused)

    def play(self):
        self._set_state(PlayerStates.Playing)

    # Override with function to call on end of stream
    def end_of_stream_event_handler(self):
        pass

    # Override with function to call on state change
    def state_change_event_handler(self):
        pass


class ControllerState:
    def __init__(self, controller, player):
        self._player = player
        self._controller = controller
        self._logger = logging.getLogger('rattlemedia')

    def __play_next_track(self):
        self._logger.info('Playing')
        try:
            # This sucks a bit. Should state own the api?
            track_url = self._controller._api.get_stream_url(self._controller._queue.popleft(), config.google_device_id)
            self._player.play_track(track_url)
        except IndexError:
            self._logger.info('Queue empty. Stopping.')
            self._player.stop()
        finally:
            self._controller.update_state()

    def play(self):
        self.__play_next_track()

    def stop(self):
        self._logger.info('Stopping')
        self._player.stop()

    def toggle(self):
        pass

    def next(self):
        self.__play_next_track()


class ControllerStatePlaying(ControllerState):
    def play(self):
        pass

    def toggle(self):
        self._player.pause()


class ControllerStateStopped(ControllerState):
    def stop(self):
        pass

    def toggle(self):
        pass


class ControllerStatePaused(ControllerState):
    def play(self):
        self._player.play()

    def toggle(self):
        self.play()


class RattleMediaController:
    _states = None

    def __init__(self):
        api = Mobileclient()
        api.login(config.google_username, config.google_password, config.google_device_id)
        self._api = api
        self._logger = logging.getLogger('rattlemedia')

        self._player = RattleMediaPlayer()
        self._player.end_of_stream_event_handler = self.end_of_stream_event
        self._player.state_change_event_handler = self.update_state

        self._queue = deque([])

        RattleMediaController._states = {PlayerStates.Paused: ControllerStatePaused(self, self._player),
                                         PlayerStates.Stopped: ControllerStateStopped(self, self._player),
                                         PlayerStates.Playing: ControllerStatePlaying(self, self._player),
                                         'Unknown': ControllerState(self, self._player)}

        self.state = ControllerState(self, self._player)
        self.update_state()

    def end_of_stream_event(self):
        self._player.stop()
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

    def next(self):
        self.state.next()

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
        current_state = None
        try:
            current_state = self._player.get_state()
            self._logger.debug('Switching state to {0}'.format(current_state))
            self.state = self._states[current_state]
            self._logger.info('Switched state to {0}'.format(self.state))
        except KeyError:
            self._logger.warn('Switching to unknown state {0}'.format(current_state))
            self.state = self._states['Unknown']
        finally:
            self.state_change_callback(current_state)

    # Override with callback if required
    def state_change_callback(self, new_state):
        pass
