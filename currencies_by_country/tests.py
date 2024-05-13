from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
import json

class TestViews(TestCase):

    def setUp(self):
        self.client = Client()

    def test_redirect_to_main(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
