from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


class StockPredictionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    @patch('api.views.get_model')
    @patch('api.views.yf.download')
    def test_predict_returns_expected_data_structure(self, mock_yf_download, mock_get_model):
        """Test that the prediction endpoint returns all expected data arrays."""
        # Create mock data that mimics yfinance output
        dates = pd.date_range(start='2020-01-01', periods=200, freq='D')
        mock_df = pd.DataFrame({
            'Date': dates,
            'Close': np.linspace(100, 200, 200) + np.random.normal(0, 5, 200),
        })
        mock_yf_download.return_value = mock_df

        # Create mock model that returns predictable predictions
        mock_model = MagicMock()
        # Model predicts 100 timesteps -> input shape (n_samples, 100, 1)
        # We need to return predictions for each test sample
        test_samples = 200 - int(200 * 0.7) - 100 + 1  # approx 51
        mock_model.predict.return_value = np.ones((test_samples, 1)) * 150
        mock_get_model.return_value = mock_model

        response = self.client.post('/api/v1/predict/', {'ticker': 'AAPL'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check status
        self.assertEqual(data['status'], 'success')

        # Check all expected keys exist
        expected_keys = [
            'historical_prices', 'historical_dates', 'ma100', 'ma200',
            'y_test', 'y_predicted', 'test_indices', 'mse', 'rmse', 'r2'
        ]
        for key in expected_keys:
            self.assertIn(key, data, f"Missing key: {key}")

        # Check arrays are lists (not numpy arrays)
        for key in ['historical_prices', 'historical_dates', 'ma100', 'ma200', 'y_test', 'y_predicted', 'test_indices']:
            self.assertIsInstance(data[key], list, f"{key} should be a list")

        # Check lengths are consistent
        self.assertEqual(len(data['historical_prices']), len(data['historical_dates']))
        self.assertEqual(len(data['historical_prices']), len(data['ma100']))
        self.assertEqual(len(data['historical_prices']), len(data['ma200']))
        self.assertEqual(len(data['y_test']), len(data['y_predicted']))
        self.assertEqual(len(data['y_test']), len(data['test_indices']))

        # Check metrics are floats
        for key in ['mse', 'rmse', 'r2']:
            self.assertIsInstance(data[key], (int, float))

        # Check test_indices is sequential
        self.assertEqual(data['test_indices'], list(range(len(data['y_test']))))

    @patch('api.views.get_model')
    @patch('api.views.yf.download')
    def test_predict_invalid_ticker_returns_404(self, mock_yf_download, mock_get_model):
        """Test that invalid ticker returns 404."""
        mock_yf_download.return_value = pd.DataFrame()  # Empty dataframe

        response = self.client.post('/api/v1/predict/', {'ticker': 'INVALID'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.json())

    def test_predict_unauthenticated_returns_401(self):
        """Test that unauthenticated request returns 401."""
        client = APIClient()  # No auth
        response = client.post('/api/v1/predict/', {'ticker': 'AAPL'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_predict_invalid_payload_returns_400(self):
        """Test that missing ticker returns 400."""
        response = self.client.post('/api/v1/predict/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ticker', response.json())