# Copyright © Idiap Research Institute <contact@idiap.ch>
#
# SPDX-License-Identifier: BSD-3-Clause
"""Test module for the MultiAuthenticator class"""
import pytest

from jinja2 import Template
from jupyterhub.auth import DummyAuthenticator
from jupyterhub.auth import PAMAuthenticator
from oauthenticator import OAuthenticator
from oauthenticator.github import GitHubOAuthenticator
from oauthenticator.gitlab import GitLabOAuthenticator
from oauthenticator.google import GoogleOAuthenticator

from ..multiauthenticator import PREFIX_SEPARATOR
from ..multiauthenticator import MultiAuthenticator


def test_different_authenticators():
    MultiAuthenticator.authenticators = [
        (
            GitLabOAuthenticator,
            "/gitlab",
            {
                "client_id": "xxxx",
                "client_secret": "xxxx",
                "oauth_callback_url": "http://example.com/hub/gitlab/oauth_callback",
            },
        ),
        (
            GitHubOAuthenticator,
            "/github",
            {
                "client_id": "xxxx",
                "client_secret": "xxxx",
                "oauth_callback_url": "http://example.com/hub/github/oauth_callback",
            },
        ),
        (PAMAuthenticator, "/pam", {"service_name": "PAM"}),
    ]

    multi_authenticator = MultiAuthenticator()
    assert len(multi_authenticator._authenticators) == 3
    assert multi_authenticator.get_custom_html("").count("\n") == 20

    routes = multi_authenticator.get_handlers("")
    assert len(routes) == 7

    authenticators = {handler.authenticator for _, handler in routes}

    assert len(authenticators) == 3

    for authenticator in authenticators:
        if isinstance(authenticator, GitLabOAuthenticator):
            assert (
                authenticator.login_url("http://example.com")
                == "http://example.com/gitlab/oauth_login"
            )
            assert (
                authenticator.logout_url("http//example.com")
                == "http//example.com/gitlab/logout"
            )
        elif isinstance(authenticator, GitHubOAuthenticator):
            assert (
                authenticator.login_url("http://example.com")
                == "http://example.com/github/oauth_login"
            )
            assert (
                authenticator.logout_url("http://example.com")
                == "http://example.com/github/logout"
            )
        elif isinstance(authenticator, PAMAuthenticator):
            assert (
                authenticator.login_url("http://example.com")
                == "http://example.com/pam/login"
            )
            assert (
                authenticator.logout_url("http://example.com")
                == "http://example.com/pam/logout"
            )
        else:
            raise ValueError(f"Unknown authenticator: {authenticator}")


def test_same_authenticators():
    MultiAuthenticator.authenticators = [
        (
            GoogleOAuthenticator,
            "/mygoogle",
            {
                "service_name": "My Google",
                "client_id": "yyyyy",
                "client_secret": "yyyyy",
                "oauth_callback_url": "http://example.com/hub/mygoogle/oauth_callback",
            },
        ),
        (
            GoogleOAuthenticator,
            "/othergoogle",
            {
                "service_name": "Other Google",
                "client_id": "xxxx",
                "client_secret": "xxxx",
                "oauth_callback_url": "http://example.com/hub/othergoogle/oauth_callback",
            },
        ),
    ]

    multi_authenticator = MultiAuthenticator()
    assert len(multi_authenticator._authenticators) == 2
    assert multi_authenticator.get_custom_html("").count("\n") == 13

    handlers = multi_authenticator.get_handlers("")
    assert len(handlers) == 6
    for path, handler in handlers:
        assert isinstance(handler.authenticator, GoogleOAuthenticator)
        if "mygoogle" in path:
            assert handler.authenticator.service_name == "My Google"
        elif "othergoogle" in path:
            assert handler.authenticator.service_name == "Other Google"
        else:
            raise ValueError(f"Unknown path: {path}")


def test_service_name():
    gitlab_service_name = "gitlab-service"
    google_service_name = "google-service"
    authenticators = [
        (
            GitLabOAuthenticator,
            "/gitlab",
            {
                "service_name": gitlab_service_name,
                "client_id": "xxxx",
                "client_secret": "xxxx",
                "oauth_callback_url": "http://example.com/hub/gitlab/oauth_callback",
            },
        ),
        (
            GoogleOAuthenticator,
            "/google",
            {
                "service_name": google_service_name,
                "client_id": "xxxx",
                "client_secret": "xxxx",
                "oauth_callback_url": "http://example.com/hub/othergoogle/oauth_callback",
            },
        ),
    ]
    MultiAuthenticator.authenticators = authenticators

    multi_authenticator = MultiAuthenticator()

    custom_html = multi_authenticator.get_custom_html("http://example.com")

    assert f"Sign in with {gitlab_service_name}" in custom_html
    assert f"Sign in with {google_service_name}" in custom_html


def test_extra_configuration():
    allowed_users = {"test_user1", "test_user2"}

    authenticators = [
        (
            GitLabOAuthenticator,
            "/gitlab",
            {
                "client_id": "xxxx",
                "client_secret": "xxxx",
                "oauth_callback_url": "http://example.com/hub/gitlab/oauth_callback",
                "allowed_users": allowed_users,
            },
        ),
        (
            PAMAuthenticator,
            "/pam",
            {
                "service_name": "PAM",
                "allowed_users": allowed_users,
            },
        ),
    ]
    MultiAuthenticator.authenticators = authenticators

    multi_authenticator = MultiAuthenticator()

    for authenticator in multi_authenticator._authenticators:
        assert authenticator.allowed_users == allowed_users


def test_username_prefix():
    MultiAuthenticator.authenticators = [
        (
            GitLabOAuthenticator,
            "/gitlab",
            {
                "client_id": "xxxx",
                "client_secret": "xxxx",
                "oauth_callback_url": "http://example.com/hub/gitlab/oauth_callback",
            },
        ),
        (PAMAuthenticator, "/pam", {"service_name": "PAM"}),
    ]

    multi_authenticator = MultiAuthenticator()
    assert len(multi_authenticator._authenticators) == 2
    assert (
        multi_authenticator._authenticators[0].username_prefix
        == f"GitLab{PREFIX_SEPARATOR}"
    )
    assert (
        multi_authenticator._authenticators[1].username_prefix
        == f"PAM{PREFIX_SEPARATOR}"
    )


@pytest.mark.asyncio
async def test_authenticated_username_prefix():
    MultiAuthenticator.authenticators = [
        (DummyAuthenticator, "/pam", {"service_name": "Dummy"}),
    ]

    multi_authenticator = MultiAuthenticator()
    assert len(multi_authenticator._authenticators) == 1
    username = await multi_authenticator._authenticators[0].authenticate(
        None, {"username": "test"}
    )
    assert username == f"Dummy{PREFIX_SEPARATOR}test"


def test_username_prefix_checks():
    MultiAuthenticator.authenticators = [
        (PAMAuthenticator, "/pam", {"service_name": "PAM", "allowed_users": {"test"}}),
        (
            PAMAuthenticator,
            "/pam",
            {"service_name": "PAM2", "blocked_users": {"test2"}},
        ),
    ]

    multi_authenticator = MultiAuthenticator()
    assert len(multi_authenticator._authenticators) == 2
    authenticator = multi_authenticator._authenticators[0]

    assert authenticator.check_allowed("test") == False
    assert authenticator.check_allowed("PAM:test") == True
    assert (
        authenticator.check_blocked_users("test") == False
    )  # Even if no block list, it does not have the correct prefix
    assert authenticator.check_blocked_users("PAM:test") == True

    authenticator = multi_authenticator._authenticators[1]
    assert authenticator.check_allowed("test2") == False
    assert (
        authenticator.check_allowed("PAM2:test2") == True
    )  # Because allowed_users is empty
    assert authenticator.check_blocked_users("test2") == False
    assert authenticator.check_blocked_users("PAM2:test2") == False


@pytest.fixture(params=[f"test me{PREFIX_SEPARATOR}", f"second{PREFIX_SEPARATOR} test"])
def invalid_name(request):
    yield request.param


def test_username_prefix_validation_with_service_name(invalid_name):
    MultiAuthenticator.authenticators = [
        (
            PAMAuthenticator,
            "/pam",
            {"service_name": invalid_name, "allowed_users": {"test"}},
        ),
    ]

    with pytest.raises(ValueError) as excinfo:
        MultiAuthenticator()

    assert f"Service name cannot contain {PREFIX_SEPARATOR}" in str(excinfo.value)


def test_username_prefix_validation_with_login_service(invalid_name):
    class MyAuthenticator(OAuthenticator):
        login_service = invalid_name

    MultiAuthenticator.authenticators = [
        (
            MyAuthenticator,
            "/myauth",
            {
                "client_id": "xxxx",
                "client_secret": "xxxx",
                "oauth_callback_url": "http://example.com/myauth/oauth_callback",
            },
        ),
    ]

    with pytest.raises(ValueError) as excinfo:
        MultiAuthenticator()

    assert f"Login service cannot contain {PREFIX_SEPARATOR}" in str(excinfo.value)


def test_next_handling():
    MultiAuthenticator.authenticators = [
        (
            PAMAuthenticator,
            "/pam",
            {"service_name": "test-service", "allowed_users": {"test"}},
        ),
    ]

    multi_authenticator = MultiAuthenticator()
    html = multi_authenticator.get_custom_html("")

    template = Template(html)

    with_next = template.render({"next": "/next-destination"})
    assert "href='pam/login?next=/next-destination'" in with_next

    without_next = template.render()
    assert "href='pam/login'" in without_next

    with_empty_next = template.render({"next": ""})
    assert "href='pam/login'" in with_empty_next
