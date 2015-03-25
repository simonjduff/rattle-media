from unittest import TestCase
from mock import patch, MagicMock
import rattlemedia


class TestController(TestCase):
    def setUp(self):
        self.patchers = []

        mobileclient_patcher = patch('rattlemedia.Mobileclient')
        self.patchers.append(mobileclient_patcher)
        mobileclient = mobileclient_patcher.start()
        mobileclient.return_value.login = MagicMock()
        self.mobileclient = mobileclient

        config_patcher = patch('rattlemedia.Config')
        self.patchers.append(config_patcher)
        config = config_patcher.start()
        config.google_username = 'test_username'
        config.google_password = 'test_password'

        self.addCleanup(self.cleanup)

    def test_creating_controller_logs_into_google(self):
        controller = rattlemedia.RattleMediaController()
        self.mobileclient.return_value.login.assert_called_once_with('test_username', 'test_password')

    def test_searcher_calls_api(self):
        controller = rattlemedia.RattleMediaController()
        controller.search('searchTerm')
        self.mobileclient.return_value.search_all_access.assert_called_once_with('searchTerm')

    def cleanup(self):
        for patcher in self.patchers:
            patcher.stop
        self.patchers = []