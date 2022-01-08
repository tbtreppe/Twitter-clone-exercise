"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_id = 1122
        self.testuser_id = self.testuser_id

        self.u1 = User.signup("abc", "test1@test.com", "password", None)
        self.u1_id = 778
        self.u1.id = self.u1_id
        self.u2 = User.signup("efg", "test2@test.com", "password", None)
        self.u2_id = 884
        self.u2.id = self.u2_id
        self.u3 = User.signup("hij", "test3@test.com", "password", None)
        self.u4 = User.signup("testing", "test4@test.com", "password", None)

        db.session.commit()
    
    def tearDown(self):
        """Clean up fouled transactions."""

        db.session.rollback()

    def test_user_index(self):
        with self.client as c:
            resp= c.get("/users")
            self.assertIn("testuser", str(resp.data))
            self.assertIn("abc", str(resp.data))
            self.assertIn("efg", str(resp.data))
            self.assertIn("hij", str(resp.data))

    def test_user_search(self):
        with self.client as c:
            resp = c.get("/users?q=test")

            self.assertIn("testuser", str(resp.data))

    def test_user_show(self):
        with self.client as c:
            resp=c.get(f"/users/{self.testuser_id}")
            
            self.assertEqual(resp.status_code, 200)
            self.assertIn("testuser", str(resp.data))

    def test_setup_likes(self):
        msg1 = Message(text="this is a message", user_id=self.testuser.id)
        msg2 = Message(text="this is another message", user_id=self.testuser.id)
        msg3 = Message(id=7777, text="different message", user_id=self.u1)
        
        db.session.add_all([msg1, msg2, msg3])
        db.session.commit()

        l1 = Likes(user_id=self.testuser.id, message_id=7777)

        db.session.add(l1)
        db.session.commit()

    def test_add_likes(self):
        m = Message(id=1984, text="message!!!", user_id=self.u1_id)
        db.session.add(m)
        db.session.commit()
    
        with self.client as c:
            with c.session_transaction() as sess:           
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post("/messages/1984/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==1984).all()
            self.assertEqual(len(likes), 1)

    def test_delete_like(self):
        self.setup_likes()

        m = Message.query.filter(Message.text=="different message").one()
        self.assertIsNotNone(m)
        self.assertNotEqual(m.user_id, self.testuser_id)

        l = Likes.query.filter(
            Likes.user_id==self.testuser_id and Likes.message_id==m.id
        ).one()

       
        self.assertIsNotNone(l)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post(f"/messages/{m.id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==m.id).all()
    
            self.assertEqual(len(likes), 0)

    def setup_followers(self):
        f1 = Follows(user_being_followed_id=self.u1_id, user_following_id=self.testuser_id)
        f2 = Follows(user_being_followed_id=self.u2_id, user_following_id=self.testuser_id)
        f3 = Follows(user_being_followed_id=self.testuser_id, user_following_id=self.u1_id)

        db.session.add_all([f1,f2,f3])
        db.session.commit()

    def test_user_show_with_follows(self):

        self.setup_followers()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("testuser", str(resp.data))

    def test_show_following(self):

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.get(f"/users/{self.testuser_id}/following")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("abc", str(resp.data))

    def test_show_followers(self):

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.get(f"/users/{self.testuser_id}/followers")

            self.assertIn("abc", str(resp.data))

    def test_unauthorized_following_page_access(self):
        self.setup_followers()
        with self.client as c:

            resp = c.get(f"/users/{self.testuser_id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))

    def test_unauthorized_followers_page_access(self):
        self.setup_followers()
        with self.client as c:

            resp = c.get(f"/users/{self.testuser_id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))

