"""Tests for Phase 2 API endpoints — auth, split-screen, ratings, admin."""

import os
import sys
import unittest
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_PATH'] = 'db/sandstone_test_routes.db'

from db.database import init_db, reset_connection, insert_study_participant, set_participant_admin


class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_routes.db'
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass
        init_db()

        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_health(self):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'ok')

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass


class TestAuthEndpoints(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_routes.db'
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass
        init_db()

        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_signup(self):
        resp = self.client.post('/auth/signup', json={
            'email': 'test@example.com',
            'password': 'TestPass123',
            'display_name': 'Test User',
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn('user_id', data)
        self.assertIn('token', data)
        self.assertIn(data['sandstone_panel'], ['A', 'B'])

    def test_signup_duplicate(self):
        self.client.post('/auth/signup', json={
            'email': 'dup@test.com', 'password': 'Pass123', 'display_name': 'D',
        })
        resp = self.client.post('/auth/signup', json={
            'email': 'dup@test.com', 'password': 'Pass123', 'display_name': 'D',
        })
        self.assertEqual(resp.status_code, 409)

    def test_login(self):
        self.client.post('/auth/signup', json={
            'email': 'login@test.com', 'password': 'Pass123', 'display_name': 'L',
        })
        resp = self.client.post('/auth/login', json={
            'email': 'login@test.com', 'password': 'Pass123',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('token', data)

    def test_login_wrong_password(self):
        self.client.post('/auth/signup', json={
            'email': 'wrong@test.com', 'password': 'Pass123', 'display_name': 'W',
        })
        resp = self.client.post('/auth/login', json={
            'email': 'wrong@test.com', 'password': 'WrongPass',
        })
        self.assertEqual(resp.status_code, 401)

    def test_login_nonexistent(self):
        resp = self.client.post('/auth/login', json={
            'email': 'nobody@test.com', 'password': 'Pass',
        })
        self.assertEqual(resp.status_code, 401)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass


class TestChatSplitEndpoint(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_routes.db'
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass
        init_db()

        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Create user and get token
        resp = self.client.post('/auth/signup', json={
            'email': 'split@test.com', 'password': 'Pass123', 'display_name': 'S',
        })
        self.token = resp.get_json()['token']
        self.user_id = resp.get_json()['user_id']

    def test_split_returns_two_responses(self):
        resp = self.client.post('/chat/split',
            json={
                'message': 'I feel devastated and heartbroken about losing my father after years of painful grief',
            },
            headers={'Authorization': f'Bearer {self.token}'}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('response_a', data)
        self.assertIn('response_b', data)
        self.assertIn('session_number', data)
        self.assertIn('exchange_number', data)
        self.assertGreater(len(data['response_a']), 0)
        self.assertGreater(len(data['response_b']), 0)

    def test_split_requires_message(self):
        resp = self.client.post('/chat/split',
            json={},
            headers={'Authorization': f'Bearer {self.token}'}
        )
        self.assertEqual(resp.status_code, 400)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass


class TestRatingsEndpoint(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_routes.db'
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass
        init_db()

        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

        resp = self.client.post('/auth/signup', json={
            'email': 'rater@test.com', 'password': 'Pass123', 'display_name': 'R',
        })
        self.token = resp.get_json()['token']
        self.user_id = resp.get_json()['user_id']

    def test_submit_rating(self):
        resp = self.client.post('/ratings',
            json={
                'session_number': 1,
                'exchange_number': 1,
                'message_text': 'test message',
                'response_a_text': 'response a',
                'response_b_text': 'response b',
                'response_a_attunement': 5,
                'response_a_contextual_accuracy': 4,
                'response_a_naturalness': 6,
                'response_b_attunement': 3,
                'response_b_contextual_accuracy': 2,
                'response_b_naturalness': 3,
                'preference': 'A',
            },
            headers={'Authorization': f'Bearer {self.token}'}
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn('rating_id', data)

    def test_get_ratings(self):
        # Submit a rating first
        self.client.post('/ratings',
            json={
                'session_number': 1, 'exchange_number': 1,
                'message_text': 'msg', 'response_a_text': 'a', 'response_b_text': 'b',
                'response_a_attunement': 4, 'response_a_contextual_accuracy': 4, 'response_a_naturalness': 4,
                'response_b_attunement': 4, 'response_b_contextual_accuracy': 4, 'response_b_naturalness': 4,
                'preference': 'none',
            },
            headers={'Authorization': f'Bearer {self.token}'}
        )

        resp = self.client.get(f'/ratings/{self.user_id}',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data['count'], 0)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass


class TestAdminEndpoints(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_routes.db'
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass
        init_db()

        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

        resp = self.client.post('/auth/signup', json={
            'email': 'admin@test.com', 'password': 'Pass123', 'display_name': 'Admin',
        })
        self.token = resp.get_json()['token']
        self.user_id = resp.get_json()['user_id']

    def test_admin_users(self):
        resp = self.client.get('/admin/users',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data['count'], 0)

    def test_admin_models(self):
        resp = self.client.get('/admin/models',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('models', data)
        self.assertIn('default', data)

    def test_admin_stats(self):
        resp = self.client.get('/admin/stats',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('total_participants', data)

    def test_admin_export(self):
        resp = self.client.get('/admin/export',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('ratings', data)
        self.assertIn('participants', data)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass


class TestLegacyEndpoints(unittest.TestCase):
    """Verify backward-compatible endpoints still work."""

    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_routes.db'
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass
        init_db()

        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_legacy_chat(self):
        resp = self.client.post('/chat', json={
            'user_id': 'legacy_user',
            'message': 'I feel devastated and heartbroken about my grief',
            'history': [],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('response', data)

    def test_legacy_baseline(self):
        resp = self.client.post('/chat/baseline', json={
            'message': 'Hello there',
            'history': [],
        })
        self.assertEqual(resp.status_code, 200)

    def test_memory_endpoint(self):
        # Create a node first via chat
        self.client.post('/chat', json={
            'user_id': 'mem_user',
            'message': 'I feel devastated and heartbroken about losing my father after years of painful grief',
            'history': [],
        })

        resp = self.client.get('/memory/mem_user')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('nodes', data)

    def test_decay_run(self):
        resp = self.client.post('/decay/run')
        self.assertEqual(resp.status_code, 200)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_routes.db')
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
