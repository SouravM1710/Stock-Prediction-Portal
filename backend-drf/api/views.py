from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import StockPredictionSerializer
from rest_framework import status
from rest_framework.response import Response

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import threading
import logging
from django.conf import settings
from .utils import save_plot

logger = logging.getLogger(__name__)

# Create your views here.

# The Keras model is loaded lazily (first prediction) and reused.
# Importing TensorFlow at startup uses ~500MB of RAM, which can exceed
# free-tier limits and kill the health check. Loading it on the first
# predict keeps boot memory low.
_model = None
_model_lock = threading.Lock()

def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = _load_model_file()
    return _model

def _load_model_file():
    """Load the trained Keras model, trying candidates in order.

    The legacy H5 is preferred: it loads deterministically across platforms.
    The .keras file is a Keras 3-format zip whose LSTM weight layout can fail
    to load under Keras 2.15 on some hosts (e.g. "lstm_cell expected 3
    variables, but received 0"). Loading is lazy (first predict), so failures
    surface as a JSON error from the predict view rather than killing boot.
    """
    from keras.models import load_model
    from importlib.metadata import version
    logger.info(
        "Loading Keras model. keras=%s tensorflow=%s",
        version('keras'), version('tensorflow'),
    )
    base_dir = settings.BASE_DIR
    for name in ('stock_prediction_model.h5', 'stock_prediction_model.keras'):
        path = os.path.join(base_dir, name)
        if os.path.exists(path):
            try:
                logger.info("Loading model from %s", name)
                return load_model(path)
            except Exception:
                logger.exception("Failed to load model from %s", name)
    raise FileNotFoundError(f"No loadable model file found in {base_dir}")


class HealthView(APIView):
    """Liveness check used by deployment hosts (Render/Railway health checks)."""
    def get(self, request):
        return Response({"status": "ok"})


class StockPredictionAPIView(APIView):
    def post(self, request):
        serializer = StockPredictionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ticker = serializer.validated_data['ticker']
        try:
            result = self._run_prediction(ticker)
            return Response(result)
        except Exception as e:
            logger.exception("Prediction failed for ticker=%s", ticker)
            return Response(
                {"error": f"{type(e).__name__}: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _run_prediction(self, ticker):
        # Heavy ML/data-science imports happen here so they don't load at boot
        import matplotlib.pyplot as plt
        from sklearn.preprocessing import MinMaxScaler
        from sklearn.metrics import mean_squared_error, r2_score

        # Fetch the data from yfinance
        now = datetime.now()
        start = datetime(now.year - 10, now.month, now.day)
        end = now
        df = yf.download(ticker, start, end, progress=False)
        if df.empty:
            return Response({"error": "No data found for the given ticker.", 'status': status.HTTP_404_NOT_FOUND})

        # yfinance >=0.2.40 returns MultiIndex columns for single tickers;
        # flatten them so df.Close is a plain Series (matching the model pipeline)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()

        # Generate basic plot
        plt.switch_backend('AGG')
        plt.figure(figsize=(12, 5))
        plt.plot(df.Close, label='Closing Price')
        plt.title(f'Closing price of {ticker}')
        plt.xlabel('Days')
        plt.ylabel('Price')
        plt.legend()

        # Save the plot to a file
        plot_img = save_plot(f'{ticker}_plot.png')

        # 100 Days moving average
        ma100 = df.Close.rolling(100).mean()
        plt.switch_backend('AGG')
        plt.figure(figsize=(12, 5))
        plt.plot(df.Close, label='Closing Price')
        plt.plot(ma100, 'r', label='100 DMA')
        plt.title(f'100 Days Moving Average of {ticker}')
        plt.xlabel('Days')
        plt.ylabel('Price')
        plt.legend()
        plot_100_dma = save_plot(f'{ticker}_100_dma.png')

        # 200 Days moving average
        ma200 = df.Close.rolling(200).mean()
        plt.switch_backend('AGG')
        plt.figure(figsize=(12, 5))
        plt.plot(df.Close, label='Closing Price')
        plt.plot(ma100, 'r', label='100 DMA')
        plt.plot(ma200, 'g', label='200 DMA')
        plt.title(f'200 Days Moving Average of {ticker}')
        plt.xlabel('Days')
        plt.ylabel('Price')
        plt.legend()
        plot_200_dma = save_plot(f'{ticker}_200_dma.png')

        # Splitting data into Training & Testing datasets
        data_training = pd.DataFrame(df.Close[0:int(len(df) * 0.7)])
        data_testing = pd.DataFrame(df.Close[int(len(df) * 0.7): int(len(df))])

        # Scaling down the data between 0 and 1
        scaler = MinMaxScaler(feature_range=(0, 1))

        # Get ML Model (loaded once and cached)
        model = get_model()

        # Preparing Test Data
        past_100_days = data_training.tail(100)
        final_df = pd.concat([past_100_days, data_testing], ignore_index=True)
        input_data = scaler.fit_transform(final_df)

        x_test = []
        y_test = []
        for i in range(100, input_data.shape[0]):
            x_test.append(input_data[i - 100: i])
            y_test.append(input_data[i, 0])
        x_test, y_test = np.array(x_test), np.array(y_test)

        # Making Predictions
        y_predicted = model.predict(x_test)

        # Revert the scaled prices to original price
        y_predicted = scaler.inverse_transform(y_predicted.reshape(-1, 1)).flatten()
        y_test = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()

        # Plot the final prediction
        plt.switch_backend('AGG')
        plt.figure(figsize=(12, 5))
        plt.plot(y_test, 'b', label='Original Price')
        plt.plot(y_predicted, 'r', label='Predicted Price')
        plt.title(f'Final Prediction for {ticker}')
        plt.xlabel('Days')
        plt.ylabel('Price')
        plt.legend()
        plot_prediction = save_plot(f'{ticker}_final_prediction.png')

        # Model Evaluation
        mse = mean_squared_error(y_test, y_predicted)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_predicted)

        return {
            'status': 'success',
            'plot_img': plot_img,
            'plot_100_dma': plot_100_dma,
            'plot_200_dma': plot_200_dma,
            'plot_prediction': plot_prediction,
            'mse': mse,
            'rmse': rmse,
            'r2': r2,
        }
