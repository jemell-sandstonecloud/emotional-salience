"""Tests for new Phase 2 database tables — participants, ratings, conversation history."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_PATH'] = 'db/sandstone_test_db_new.db'

from db.database import (
    init_db, reset_connection,
    insert_study_participant, get_study_participant, get_study_participant_by_email,
    get_all_study_participants, update_participant_session_count, update_participant_exchange_count,
    set_participant_consent, set_participant_admin,
    insert_rating, get_ratings_by_user, get_all_ratings,
    insert_conversation_turn, get_conversation_history, get_latest_session_number,
    _hash_password,
)


class TestStudyParticipants(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_db_new.db'
        try:
            os.remove('db/sandstone_test_db_new.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_insert_and_get(self):
        uid = insert_study_participant('user1', 'test@test.com', 'Tester', 'A', 'password123')
        self.assertEqual(uid, 'user1')

        p = get_study_participant('user1')
        self.assertIsNotNone(p)
        self.assertEqual(p['email'], 'test@test.com')
        self.assertEqual(p['display_name'], 'Tester')
        self.assertEqual(p['sandstone_panel'], 'A')

    def test_get_by_email(self):
        insert_study_participant('user2', 'alice@test.com', 'Alice', 'B', 'pass')
        p = get_study_participant_by_email('alice@test.com')
        self.assertIsNotNone(p)
        self.assertEqual(p['user_id'], 'user2')

    def test_get_nonexistent(self):
        p = get_study_participant('nonexistent')
        self.assertIsNone(p)

    def test_get_all(self):
        insert_study_participant('u1', 'a@t.com', 'A', 'A', 'p')
        insert_study_participant('u2', 'b@t.com', 'B', 'B', 'p')
        all_p = get_all_study_participants()
        self.assertEqual(len(all_p), 2)

    def test_panel_is_a_or_b(self):
        insert_study_participant('u3', 'c@t.com', 'C', 'A', 'p')
        p = get_study_participant('u3')
        self.assertIn(p['sandstone_panel'], ['A', 'B'])

    def test_session_count_increment(self):
        insert_study_participant('u4', 'd@t.com', 'D', 'A', 'p')
        update_participant_session_count('u4')
        update_participant_session_count('u4')
        p = get_study_participant('u4')
        self.assertEqual(p['session_count'], 2)

    def test_exchange_count_increment(self):
        insert_study_participant('u5', 'e@t.com', 'E', 'B', 'p')
        update_participant_exchange_count('u5')
        p = get_study_participant('u5')
        self.assertEqual(p['total_exchanges'], 1)

    def test_consent(self):
        insert_study_participant('u6', 'f@t.com', 'F', 'A', 'p')
        set_participant_consent('u6')
        p = get_study_participant('u6')
        self.assertIsNotNone(p['consent_given_at'])

    def test_admin_flag(self):
        insert_study_participant('u7', 'g@t.com', 'G', 'A', 'p')
        set_participant_admin('u7', True)
        p = get_study_participant('u7')
        self.assertEqual(p['is_admin'], 1)

    def test_password_hash(self):
        h1 = _hash_password('test123')
        h2 = _hash_password('test123')
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, 'test123')

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_db_new.db')
        except FileNotFoundError:
            pass


class TestStudyRatings(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_ratings.db'
        try:
            os.remove('db/sandstone_test_ratings.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_insert_and_get(self):
        rid = insert_rating(
            user_id='user1', session_number=1, exchange_number=1,
            message_text='test message',
            response_a_text='response A', response_b_text='response B',
            response_a_attunement=5, response_a_contextual_accuracy=4, response_a_naturalness=6,
            response_b_attunement=3, response_b_contextual_accuracy=2, response_b_naturalness=3,
            preference='A', which_is_sandstone='A',
            memory_state_snapshot=[{'topic': 'grief', 'salience': 0.8}],
            model_id='us.anthropic.claude-sonnet-4-5-v1'
        )
        self.assertIsNotNone(rid)

        ratings = get_ratings_by_user('user1')
        self.assertEqual(len(ratings), 1)
        r = ratings[0]
        self.assertEqual(r['response_a_attunement'], 5)
        self.assertEqual(r['preference'], 'A')
        self.assertEqual(r['which_is_sandstone'], 'A')

    def test_get_all_ratings(self):
        for i in range(3):
            insert_rating(
                user_id=f'user{i}', session_number=1, exchange_number=1,
                message_text='msg', response_a_text='a', response_b_text='b',
                response_a_attunement=4, response_a_contextual_accuracy=4, response_a_naturalness=4,
                response_b_attunement=4, response_b_contextual_accuracy=4, response_b_naturalness=4,
                preference='none', which_is_sandstone='A',
            )
        all_r = get_all_ratings()
        self.assertEqual(len(all_r), 3)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_ratings.db')
        except FileNotFoundError:
            pass


class TestConversationHistory(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_convhist.db'
        try:
            os.remove('db/sandstone_test_convhist.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_insert_and_get(self):
        insert_conversation_turn('user1', 1, 'sandstone', 'user', 'Hello', 1)
        insert_conversation_turn('user1', 1, 'sandstone', 'assistant', 'Hi there!', 1)

        hist = get_conversation_history('user1', 1, 'sandstone')
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0]['role'], 'user')
        self.assertEqual(hist[1]['role'], 'assistant')

    def test_panel_isolation(self):
        insert_conversation_turn('user1', 1, 'sandstone', 'user', 'Hello sand', 1)
        insert_conversation_turn('user1', 1, 'baseline', 'user', 'Hello base', 1)

        sand = get_conversation_history('user1', 1, 'sandstone')
        base = get_conversation_history('user1', 1, 'baseline')
        self.assertEqual(len(sand), 1)
        self.assertEqual(len(base), 1)
        self.assertIn('sand', sand[0]['content'])
        self.assertIn('base', base[0]['content'])

    def test_session_number(self):
        insert_conversation_turn('user1', 1, 'sandstone', 'user', 'Session 1', 1)
        insert_conversation_turn('user1', 2, 'sandstone', 'user', 'Session 2', 1)

        latest = get_latest_session_number('user1')
        self.assertEqual(latest, 2)

    def test_no_sessions(self):
        latest = get_latest_session_number('nobody')
        self.assertEqual(latest, 0)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_convhist.db')
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
