from django.test import TestCase
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()

class AuthTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin',
            password='testpassword123',
            email='admin@example.com'
        )

    def test_user_creation(self):
        """Test that the user was created correctly"""
        u = User.objects.get(username='admin')
        self.assertEqual(u.username, 'admin')
        self.assertTrue(u.is_active)
        self.assertTrue(u.check_password('testpassword123'))

    def test_authentication(self):
        """Test that the user can authenticate via the backend"""
        user = authenticate(username='admin', password='testpassword123')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'admin')

    def test_invalid_authentication(self):
        """Test that invalid credentials fail"""
        user = authenticate(username='admin', password='wrongpassword')
        self.assertIsNone(user)
