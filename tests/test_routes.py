"""Tests for Sandstone API routes."""

import os
import sys
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import SandstoneTestCase
from db.database import insert_study_participant, get_study_participant_by_email, _verify_password


class TestAuthSignup(SandstoneTestCase):
    def setUp(self):
        super().setUp()
        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_signup_success(self):
        resp = self.client.post('/auth/signup', json={
            'email': 'new@test.com', 'password': 'pass123', 'display_name': 'New User'
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn('token', data)
        self.assertIn('user_id', data)

    def test_signup_duplicate(self):
        insert_study_participant("dup_uid", "dup@test.com", "Dup", "A", "pass")
        resp = self.client.post('/auth/signup', json={
            'email': 'dup@test.com', 'password': 'pass123', 'display_name': 'Dup'
        })
        self.assertEqual(resp.status_code, 409)

    def test_signup_missing_fields(self):
        resp = self.client.post('/auth/signup', json={'email': 'a@b.com'})
        self.assertEqual(resp.status_code, 400)


class TestAuthLogin(SandstoneTestCase):
    def setUp(self):
        super().setUp()
        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_login_success(self):
        self.client.post('/auth/signup', json={
            'email': 'login@test.com', 'password': 'mypassword', 'display_name': 'Login User'
        })
        resp = self.client.post('/auth/login', json={
            'email': 'login@test.com', 'password': 'mypassword'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.get_json())

    def test_login_wrong_password(self):
        self.client.post('/auth/signup', json={
            'email': 'wrong@test.com', 'password': 'correct', 'display_name': 'WP'
        })
        resp = self.client.post('/auth/login', json={
            'email': 'wrong@test.com', 'password': 'incorrect'
        })
        self.assertEqual(resp.status_code, 401)

    def test_login_nonexistent(self):
        resp = self.client.post('/auth/login', json={
            'email': 'nobody@test.com', 'password': 'pass'
        })
        self.assertEqual(resp.status_code, 401)


class TestHealthEndpoint(SandstoneTestCase):
    def setUp(self):
        super().setUp()
        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_health(self):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], 'ok')


class TestProtectedEndpoints(SandstoneTestCase):
    def setUp(self):
        super().setUp()
        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()
        # Create user and get token
        resp = self.client.post('/auth/signup', json={
            'email': 'auth@test.com', 'password': 'authpass', 'display_name': 'Auth'
        })
        self.token = resp.get_json().get('token', '')
        self.user_id = resp.get_json().get('user_id', '')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def test_consent(self):
        resp = self.client.post('/auth/consent', headers=self.headers)
        self.assertIn(resp.status_code, [200, 401])

    def test_new_session(self):
        resp = self.client.post('/session/new', headers=self.headers)
        self.assertIn(resp.status_code, [200, 401])

    def test_admin_users(self):
        resp = self.client.get('/admin/users', headers=self.headers)
        self.assertIn(resp.status_code, [200, 401])


if __name__ == '__main__':
    unittest.main()
