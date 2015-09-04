"""Farcy objects test file."""

from __future__ import print_function
from farcy import objects
from mock import patch
import unittest
import farcy.exceptions as exceptions


class ConfigTest(unittest.TestCase):
    """Tests Config helper."""

    @patch('farcy.objects.ConfigParser')
    @patch('os.path.isfile')
    def _config_instance(self, callback, mock_is_file, mock_config, repo=None,
                         post_callback=None, **overrides):
        mock_is_file.called_with(objects.Config.PATH).return_value = True

        if callback:
            callback(mock_config.return_value)
        config = objects.Config(repo, **overrides)
        if post_callback:
            post_callback(mock_config.return_value)
        self.assertTrue(mock_config.called)
        return config

    def test_cant_change_log_level_if_debug(self):
        config = self._config_instance(None, repo='a/b')
        self.assertNotEqual('DEBUG', config.log_level)
        config.debug = True
        self.assertEqual('DEBUG', config.log_level)
        config.log_level = 'WARNING'
        self.assertEqual('DEBUG', config.log_level)

    def test_config_file_is_overridable(self):
        def callback(mock_config):
            mock_config.items.return_value = {'start_event': '1337'}
        config = self._config_instance(callback, repo='a/b')
        self.assertEqual(1337, config.start_event)
        config.start_event = 10
        self.assertEqual(10, config.start_event)

    def test_config_file_repo_specific_works(self):
        def callback(mock_config):
            mock_config.has_section.return_value = True
            mock_config.items.return_value = {'start_event': '1337'}

        def post_callback(mock_config):
            mock_config.items.assert_called_with('a/b')
        config = self._config_instance(callback, repo='a/b',
                                       post_callback=post_callback)
        self.assertEqual('a/b', config.repository)
        self.assertEqual(1337, config.start_event)

    def test_config_file_values(self):
        def callback(mock_config):
            mock_config.has_section.return_value = False
            mock_config.items.return_value = {
                'start_event': '10', 'debug': True,
                'exclude_paths': 'node_modules,vendor',
                'limit_users': 'balloob,bboe', 'log_level': 'DEBUG',
                'pr_issue_report_limit': '100'}

        def post_callback(mock_config):
            mock_config.items.assert_called_with('DEFAULT')
        config = self._config_instance(callback, repo='a/b',
                                       post_callback=post_callback)
        self.assertEqual('a/b', config.repository)
        self.assertEqual(10, config.start_event)
        self.assertEqual(True, config.debug)
        self.assertEqual({'node_modules', 'vendor'}, config.exclude_paths)
        self.assertEqual({'balloob', 'bboe'}, config.limit_users)
        self.assertEqual('DEBUG', config.log_level)
        self.assertEqual(100, config.pr_issue_report_limit)

    def test_config__overrides(self):
        config = self._config_instance(None, repo='a/b', start_event=1337,
                                       limit_users='bboe')
        self.assertEqual('a/b', config.repository)
        self.assertEqual(1337, config.start_event)
        self.assertEqual({'bboe'}, config.limit_users)

    def test_config__repr(self):
        config = self._config_instance(None, repo='a/b')
        repr_str = ("Config('a/b', debug=False, exclude_paths=None, "
                    "limit_users=None, log_level='ERROR', "
                    "pr_issue_report_limit=128, pull_requests=None, "
                    "start_event=None)")
        self.assertEqual(repr_str, repr(config))

    def test_default_repo_from_config(self):
        def callback(mock_config):
            mock_config.get.return_value = 'appfolio/farcy'
        config = self._config_instance(callback)
        self.assertEqual('appfolio/farcy', config.repository)

    def test_default_repo_from_config_raise_on_invalid(self):
        def callback(mock_config):
            mock_config.get.return_value = 'invalid_repo'
        with self.assertRaises(exceptions.FarcyException):
            self._config_instance(callback)

    def test_raise_if_invalid_log_level(self):
        config = self._config_instance(None, repo='a/b')
        with self.assertRaises(exceptions.FarcyException):
            config.log_level = 'invalid_log_level'

    def test_raise_if_invalid_repository(self):
        config = self._config_instance(None, repo='a/b')
        with self.assertRaises(exceptions.FarcyException):
            config.repository = 'invalid_repo'

    def test_setting_repo(self):
        config = self._config_instance(None, repo='a/b')
        self.assertEqual('a/b', config.repository)
        config.repository = 'appfolio/farcy'
        self.assertEqual('appfolio/farcy', config.repository)

    def test_setting_values_via_dict(self):
        config = self._config_instance(None, repo='appfolio/farcy')
        data = {
            'start_event': 1000,
            'debug': False,
            'exclude_paths': {'npm_modules', 'vendor'},
            'limit_users': {'balloob', 'bboe'},
            'log_level': 'WARNING',
            'pr_issue_report_limit': 100
        }

        config.override(**data)
        for attr, value in data.items():
            self.assertEqual(value, getattr(config, attr))

    def test_user_whitelisted_passes_if_not_set(self):
        config = self._config_instance(None, repo='a/b')
        self.assertTrue(config.user_whitelisted('balloob'))

    def test_user_whitelisted_works_if_set(self):
        config = self._config_instance(None, repo='a/b')
        config.limit_users = ['bboe', 'balloob']
        self.assertTrue(config.user_whitelisted('balloob'))
        self.assertFalse(config.user_whitelisted('appfolio'))


class ErrorMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = objects.ErrorMessage('Dummy Message')

    def add_lines(self, on_github, *lines):
        for line in lines:
            self.message.track(line, on_github)

    def assert_counts(self, total, github, new):
        self.assertEqual(total, len(self.message))
        self.assertEqual(github, self.message.count_github())
        self.assertEqual(new, self.message.count_new())

    def test_messages__group_consequtive(self):
        self.add_lines(False, 1, 2, 3)
        self.assertEqual([(1, 'Dummy Message <sub>3x spanning 3 lines</sub>')],
                         list(self.message.messages()))

    def test_messages__group_span(self):
        self.add_lines(False, 1, 3, 5)
        self.assertEqual([(1, 'Dummy Message <sub>3x spanning 5 lines</sub>')],
                         list(self.message.messages()))

    def test_messages__no_grouping(self):
        self.add_lines(False, 1, 4, 100, 105)
        self.assertEqual([(1, 'Dummy Message'), (4, 'Dummy Message'),
                          (100, 'Dummy Message'), (105, 'Dummy Message')],
                         list(self.message.messages()))

    def test_no_messages(self):
        self.assert_counts(0, 0, 0)

    def test_track_and_counts__multiple_messages(self):
        self.add_lines(False, 16, 1, 28)
        self.add_lines(True, 17, 1, 27)
        self.assert_counts(5, 3, 2)

    def test_track_and_counts__single_github_message(self):
        self.message.track(15, on_github=True)
        self.assert_counts(1, 1, 0)

    def test_track_and_counts__single_message_on_both(self):
        self.message.track(15, on_github=True)
        self.message.track(15, on_github=False)
        self.assert_counts(1, 1, 0)

    def test_track_and_counts__single_new_message(self):
        self.message.track(15)
        self.assert_counts(1, 0, 1)

    def test_track__return_value(self):
        self.assertEqual(self.message, self.message.track(16))
