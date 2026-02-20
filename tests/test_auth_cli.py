"""Tests for authentication-related Flask CLI commands."""

import os

import app as app_module
from app import find_user_by_username, load_users


class TestAuthCLI:
    """Tests for user admin CLI commands."""

    def test_missing_users_store_initializes_empty(self, app):
        """Missing users store should initialize with no default user."""
        if os.path.exists(app_module.USERS_FILE):
            os.remove(app_module.USERS_FILE)

        users = load_users()
        assert users == []
        assert find_user_by_username('admin') is None

    def test_create_user_command_success(self, runner):
        """Create-user command adds a new user with hashed password."""
        result = runner.invoke(
            args=['create-user', 'alice'],
            input='strongpass123\nstrongpass123\n'
        )

        assert result.exit_code == 0
        assert "User 'alice' created." in result.output

        user = find_user_by_username('alice')
        assert user is not None
        assert 'password' not in user
        assert app_module.verify_password(user['password_hash'], 'strongpass123')

    def test_create_user_command_duplicate_fails(self, runner):
        """Create-user command fails for duplicate usernames."""
        first = runner.invoke(
            args=['create-user', 'alice'],
            input='strongpass123\nstrongpass123\n'
        )
        assert first.exit_code == 0

        second = runner.invoke(
            args=['create-user', 'alice'],
            input='anotherpass123\nanotherpass123\n'
        )
        assert second.exit_code != 0
        assert 'User already exists' in second.output

    def test_reset_password_command_success(self, runner):
        """Reset-password updates password hash for existing user."""
        result = runner.invoke(
            args=['reset-password', 'testuser'],
            input='newsecret123\nnewsecret123\n'
        )

        assert result.exit_code == 0
        assert "Password updated for 'testuser'." in result.output

        user = find_user_by_username('testuser')
        assert user is not None
        assert app_module.verify_password(user['password_hash'], 'newsecret123')

    def test_reset_password_command_missing_user_fails(self, runner):
        """Reset-password fails when user does not exist."""
        result = runner.invoke(
            args=['reset-password', 'missing-user'],
            input='newsecret123\nnewsecret123\n'
        )

        assert result.exit_code != 0
        assert "User 'missing-user' not found." in result.output
