from unittest import TestCase
from mock import patch, MagicMock
import rattlemedia


class TestController(TestCase):
    def setUp(self):
        self.patchers = []

        mobile_client_patcher = patch('rattlemedia.Mobileclient')
        self.patchers.append(mobile_client_patcher)
        mobile_client = mobile_client_patcher.start()
        mobile_client.return_value.login = MagicMock()
        self.mobile_client = mobile_client

        config_patcher = patch('rattlemedia.Config')
        self.patchers.append(config_patcher)
        config = config_patcher.start()
        config.google_username = 'test_username'
        config.google_password = 'test_password'

        self.controller = rattlemedia.RattleMediaController()

        self.addCleanup(self.cleanup)

    def test_creating_controller_logs_into_google(self):
        self.mobile_client.return_value.login.assert_called_once_with('test_username', 'test_password')

    def test_searcher_calls_api(self):
        self.controller.search('searchTerm')
        self.mobile_client.return_value.search_all_access.assert_called_once_with('searchTerm')

    def test_enqueue_adds_to_queue(self):
        pass
        # Todo create a new MusicPlayer class to encapsulate media state away from the controller

    def cleanup(self):
        for patcher in self.patchers:
            patcher.stop
        self.patchers = []