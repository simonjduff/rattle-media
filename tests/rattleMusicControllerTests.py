from unittest import TestCase
from mock import patch, MagicMock
import rattlemediaplayer
from gi.repository import Gst
import logging
import sys
from collections import deque
import gevent
from rattlemediaplayer import PlayerStates

logger = None

def setup_logging():
    global logger
    log_formatter = logging.Formatter('[%(asctime)s] %(levelname)s (%(process)d) %(module)s %(funcName)s: %(message)s')
    stream_handle = logging.StreamHandler(sys.stdout)
    stream_handle.setLevel(logging.DEBUG)
    stream_handle.setFormatter(log_formatter)
    logger = logging.getLogger('rattlemedia')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stream_handle)

setup_logging()


class TestBase(TestCase):
    fake_song_urls = {'12345': 'http://testurl1.example.com', '67890': 'http://testurl2.example.com'}
    fake_albums = {'album1': {'tracks':[{'nid': 'track1'}, {'nid': 'track2'}]}}

    def add_bus_message(self, message_type):
        message = type('Gst.Message', (), {})()
        message.type = message_type
        print 'Adding message {0}'.format(message_type)
        self.bus_messages.append(message)

    def pop_bus_message(self):
        try:
            message = self.bus_messages.popleft()
        except IndexError:
            message = None

        if message:
            print 'Popping message {0}'.format(message.type)

        return message

    def setUp(self):
        def get_fake_url(song_id, device_id):
            return TestController.fake_song_urls[song_id]

        def get_fake_album(album_id):
            return TestController.fake_albums[album_id]

        def set_state(state):
            self.player.state = state

        def get_state(timeout):
            return (Gst.StateChangeReturn.SUCCESS, self.player.state, Gst.State.NULL)

        self.patchers = []
        self.bus_messages = deque([])

        mobile_client_patcher = patch('rattlemediaplayer.Mobileclient')
        self.patchers.append(mobile_client_patcher)
        mobile_client = mobile_client_patcher.start()
        mobile_client.return_value.get_stream_url = MagicMock(side_effect=get_fake_url)
        mobile_client.return_value.get_album_info = MagicMock(side_effect=get_fake_album)
        self.mobile_client = mobile_client

        config_patcher = patch('rattlemediaplayer.config')
        self.patchers.append(config_patcher)
        config = config_patcher.start()
        config.google_username = 'test_username'
        config.google_password = 'test_password'
        config.google_device_id = 'test_device_id'
        self.config = config

        self.player = MagicMock()
        self.player.set_state = set_state
        self.player.get_state = get_state
        self.player.get_bus.return_value.pop = self.pop_bus_message
        player_make_patcher = patch.object(rattlemediaplayer.Gst.ElementFactory, 'make')
        self.patchers.append(player_make_patcher)
        player_make = player_make_patcher.start()
        player_make.return_value = self.player

        self.controller = rattlemediaplayer.RattleMediaController()

        self.addCleanup(self.cleanup)

    def cleanup(self):
        while self.patchers:
            patcher = self.patchers.pop()
            patcher.stop()


class TestStopped(TestBase):
    def test_initial_state(self):
        self.assertEqual(0, len(self.controller._queue))
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)

    def test_enqueue(self):
        self.controller.enqueue('12345')
        self.assertEqual(1, len(self.controller._queue))
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)

    def test_play_empty(self):
        self.controller.play()
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)

    def test_play_with_song(self):
        self.controller.enqueue('12345')
        self.controller.play()
        self.assertEqual(self.controller._states[PlayerStates.Playing], self.controller.state)
        self.assertEqual(0, len(self.controller._queue))

    def test_stop_stays_stopped(self):
        self.controller.stop()
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)

    def test_toggle_stays_stopped(self):
        self.controller.toggle_playback()
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)

    def test_next_stays_stopped(self):
        self.controller.next()
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)


class TestPlaying(TestBase):
    def setUp(self):
        TestBase.setUp(self)
        self.player.state = Gst.State.PLAYING
        self.controller.update_state()

    def test_initial_state(self):
        self.assertEqual(self.controller._states[PlayerStates.Playing], self.controller.state)

    def test_eos_plays_next_track(self):
        self.controller.enqueue('12345')
        TestBase.add_bus_message(self, Gst.MessageType.EOS)
        # We need to give the greenlet polling mechanism time to check for a message
        gevent.sleep(0.5)
        self.assertEqual(self.controller._states[PlayerStates.Playing], self.controller.state)
        self.assertEqual(0, len(self.controller._queue))

    def test_eos_empty_queue_stops(self):
        TestBase.add_bus_message(self, Gst.MessageType.EOS)
        # We need to give the greenlet polling mechanism time to check for a message
        gevent.sleep(0.5)
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)

    def test_stop_stops(self):
        self.controller.stop()
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)

    def test_toggle_pauses(self):
        self.controller.toggle_playback()
        self.assertEqual(self.controller._states[PlayerStates.Paused], self.controller.state)

    def test_next_empty_queue_stops(self):
        self.controller.next()
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)
        self.assertEqual(0, len(self.controller._queue))

    def test_next_plays_next_track(self):
        self.controller.enqueue('12345')
        self.controller.next()
        self.assertEqual(self.controller._states[PlayerStates.Playing], self.controller.state)
        self.assertEqual(0, len(self.controller._queue))



class TestPaused(TestBase):
    def setUp(self):
        TestBase.setUp(self)
        self.player.state = Gst.State.PAUSED
        self.controller.update_state()

    def test_initial_state(self):
        self.assertEqual(self.controller._states[PlayerStates.Paused], self.controller.state)

    def test_stop_stops(self):
        self.controller.stop()
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)

    def test_toggle_plays(self):
        self.controller.toggle_playback()
        self.assertEqual(self.controller._states[PlayerStates.Playing], self.controller.state)


class TestController(TestBase):
    def test_creating_controller_logs_into_google(self):
        self.mobile_client.return_value.login.assert_called_once_with('test_username', 'test_password', 'test_device_id')

    def test_creating_controller_sets_state_null(self):
        self.assertEqual(Gst.State.NULL, self.player.state)

    def test_searcher_calls_api(self):
        self.controller.search('searchTerm')
        self.mobile_client.return_value.search_all_access.assert_called_once_with('searchTerm')

    def test_enqueue_adds_to_queue(self):
        song_id = '12345'
        song_id_2 = '12345'
        self.controller.enqueue(song_id)
        self.assertEqual(1, len(self.controller._queue))
        self.assertEqual(song_id, self.controller._queue[0])
        self.controller.enqueue(song_id_2)
        self.assertEqual(2, len(self.controller._queue))
        self.assertEqual(song_id_2, self.controller._queue[1])

    def test_enqueue_album_queues_album(self):
        self.controller.enqueue_album('album1')
        self.mobile_client.return_value.get_album_info.assert_called_once_with('album1')
        self.assertEqual(2, len(self.controller._queue))
        self.assertEqual('track1', self.controller._queue[0])
        self.assertEqual('track2', self.controller._queue[1])
        self.assertEqual(self.controller._states[PlayerStates.Stopped], self.controller.state)