#!/usr/bin/env python3
"""
Unit and integration tests for the `client.py` module.
"""
import unittest
from unittest.mock import patch, PropertyMock, Mock
from parameterized import parameterized, parameterized_class
from client import GithubOrgClient
from fixtures import TEST_PAYLOAD
from typing import Dict


class TestGithubOrgClient(unittest.TestCase):
    """
    Unit tests for the GithubOrgClient class.
    """

    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    @patch('client.get_json')
    def test_org(self, org_name: str, mock_get_json: Mock) -> None:
        """
        Test that GithubOrgClient.org returns the correct value.
        Ensures get_json is called once with expected argument.
        """
        test_client = GithubOrgClient(org_name)
        test_client.org()
        mock_get_json.assert_called_once_with(
            f"https://api.github.com/orgs/{org_name}"
        )

    def test_public_repos_url(self) -> None:
        """
        Test that _public_repos_url returns the correct repos_url
        based on the mocked org payload.
        """
        known_payload = {"repos_url": "http://example.com/repos"}
        with patch(
            'client.GithubOrgClient.org',
            new_callable=PropertyMock
        ) as mock_org:
            mock_org.return_value = known_payload
            test_client = GithubOrgClient("test_org")
            result = test_client._public_repos_url
            self.assertEqual(result, "http://example.com/repos")

    @patch('client.get_json')
    def test_public_repos(self, mock_get_json: Mock) -> None:
        """
        Test public_repos returns list of repo names from payload.
        Ensure get_json and _public_repos_url are called once.
        """
        test_payload = [{"name": "repo1"}, {"name": "repo2"}]
        mock_get_json.return_value = test_payload

        with patch(
            'client.GithubOrgClient._public_repos_url',
            new_callable=PropertyMock
        ) as mock_public_repos_url:
            mock_public_repos_url.return_value = (
                "http://example.com/repos"
            )
            test_client = GithubOrgClient("test_org")
            result = test_client.public_repos()
            self.assertEqual(result, ["repo1", "repo2"])
            mock_get_json.assert_called_once_with(
                "http://example.com/repos"
            )
            mock_public_repos_url.assert_called_once()

    @parameterized.expand([
        ({"license": {"key": "my_license"}}, "my_license", True),
        ({"license": {"key": "other_license"}}, "my_license", False),
    ])
    def test_has_license(self, repo: Dict, license_key: str, expected: bool) -> None:
        """
        Test has_license returns True or False based on license_key.
        """
        result = GithubOrgClient.has_license(repo, license_key)
        self.assertEqual(result, expected)


@parameterized_class(
    ("org_payload", "repos_payload", "expected_repos", "apache2_repos"),
    TEST_PAYLOAD
)
class TestIntegrationGithubOrgClient(unittest.TestCase):
    """
    Integration tests for GithubOrgClient.public_repos using fixtures.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Set up the mock for requests.get to return payloads based on URL.
        """
        def side_effect(url):
            mock_response = Mock()
            org_url = "https://api.github.com/orgs/google"
            if url == org_url:
                mock_response.json.return_value = cls.org_payload
            elif url == cls.org_payload["repos_url"]:
                mock_response.json.return_value = cls.repos_payload
            else:
                mock_response.status_code = 404
            return mock_response

        cls.get_patcher = patch('requests.get', side_effect=side_effect)
        cls.mock_get = cls.get_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Stop the patcher after tests.
        """
        cls.get_patcher.stop()

    def test_public_repos(self) -> None:
        """
        Test public_repos without license filter returns expected repos.
        """
        test_client = GithubOrgClient("google")
        result = test_client.public_repos()
        self.assertEqual(result, self.expected_repos)

    def test_public_repos_with_license(self) -> None:
        """
        Test public_repos with license filter returns expected repos.
        """
        test_client = GithubOrgClient("google")
        result = test_client.public_repos(license="apache-2.0")
        self.assertEqual(result, self.apache2_repos)
