from unittest import TestCase
from mock import patch, MagicMock, call
import rattlemedia
import gst


class TestController(TestCase):
    fake_song_urls = {'12345': 'http://testurl1.example.com', '67890': 'http://testurl2.example.com'}

    def setUp(self):
        self.patchers = []

        mobile_client_patcher = patch('rattlemedia.Mobileclient')
        self.patchers.append(mobile_client_patcher)
        mobile_client = mobile_client_patcher.start()
        mobile_client.return_value.login = MagicMock()
        mobile_client.return_value.get_stream_url = MagicMock(side_effect=self.get_fake_url)
        self.mobile_client = mobile_client

        config_patcher = patch('rattlemedia.config')
        self.patchers.append(config_patcher)
        config = config_patcher.start()
        config.google_username = 'test_username'
        config.google_password = 'test_password'
        self.config = config

        player_patcher = patch.object(rattlemedia.RattleMediaController, '_player')
        self.patchers.append(player_patcher)
        self.player = player_patcher.start()

        self.controller = rattlemedia.RattleMediaController()

        self.addCleanup(self.cleanup)

    def get_fake_url(self, song_id, device_id):
        return TestController.fake_song_urls[song_id]

    def test_creating_controller_logs_into_google(self):
        self.mobile_client.return_value.login.assert_called_once_with('test_username', 'test_password')

    def test_creating_controller_sets_state_null(self):
        self.player.set_state.assert_called_once_with(gst.STATE_NULL)

    def test_searcher_calls_api(self):
        self.controller.search('searchTerm')
        self.mobile_client.return_value.search_all_access.assert_called_once_with('searchTerm')

    def test_enqueue_adds_to_queue(self):
        song_id = '12345'
        self.controller.enqueue(song_id)
        self.assertEqual(1, len(self.controller._music_player.queue))
        self.assertEqual(song_id, self.controller._music_player.queue[0])

    def test_play_with_one_song_plays_song(self):
        self.controller.enqueue('12345')
        self.controller.play()
        self.mobile_client.return_value.get_stream_url.assert_called_once_with('12345', self.config.google_device_id)
        self.player.set_state.assert_has_calls([call(gst.STATE_NULL), call(gst.STATE_PLAYING)])
        self.player.set_property.assert_called_once_with('uri', TestController.fake_song_urls['12345'])
        self.assertEqual(0, len(self.controller._music_player.queue))

    def test_Empty_queue_doesnt_play(self):
        self.controller.play()
        self.player.set_state.assert_called_once_with(gst.STATE_NULL)

    def test_stop_nulls_state(self):
        self.controller.stop()
        self.player.set_state.assert_has_calls([call(gst.STATE_NULL), call(gst.STATE_NULL)])

    def test_toggle_when_playing_pauses(self):
        self.controller.enqueue('12345')
        self.controller.play()
        self.player.set_state.assert_has_calls([call(gst.STATE_NULL), call(gst.STATE_PLAYING)])
        self.controller.toggle_playback()
        self.player.set_state.assert_has_calls([call(gst.STATE_NULL), call(gst.STATE_PLAYING), call(gst.STATE_PAUSED)])

    def cleanup(self):
        while self.patchers:
            patcher = self.patchers.pop()
            patcher.stop()