from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import StockPredictionSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import threading
import logging
from django.conf import settings
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score

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
    # Configure TensorFlow for minimal memory before any TF import
    import os as _os
    _os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
    _os.environ.setdefault('TF_NUM_INTRAOP_THREADS', '1')
    _os.environ.setdefault('TF_NUM_INTEROP_THREADS', '1')
    # Force TF to use a small per-process GPU/CPU memory fraction
    _os.environ.setdefault('TF_GPU_ALLOCATOR', 'cuda_malloc_async')  # no-op on CPU

    from keras.models import load_model
    from importlib.metadata import version
    import tensorflow as tf

    # Limit TensorFlow memory growth and visible devices (CPU only)
    try:
        tf.config.set_visible_devices([], 'GPU')  # disable GPU entirely
        # Limit CPU memory allocator
        tf.config.threading.set_intra_op_parallelism_threads(1)
        tf.config.threading.set_inter_op_parallelism_threads(1)
    except Exception:
        pass  # ignore if TF not fully initialized yet

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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StockPredictionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ticker = serializer.validated_data['ticker']
        try:
            result = self._run_prediction(ticker)
            # JSON-encode here, inside the try, so any encoding failure (e.g.
            # numpy>=2's float64 no longer being a float subclass) becomes a
            # JSON error with the real message instead of escaping the view as
            # a raw 500 during DRF's post-view response rendering.
            result = json.loads(json.dumps(result, default=float))
            return Response(result)
        except ValueError as e:
            # Invalid ticker / no data — return 404 without version leak
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except MemoryError as e:
            # OOM during model load or prediction — return structured error
            logger.exception("MemoryError during prediction for ticker=%s", ticker)
            return Response(
                {"error": "Server memory limit exceeded. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.exception("Prediction failed for ticker=%s", ticker)
            return Response(
                {"error": f"{type(e).__name__}: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _run_prediction(self, ticker):
        # Fetch the data from yfinance (with retries for transient failures)
        now = datetime.now()
        start = datetime(now.year - 10, now.month, now.day)
        end = now
        df = None
        for attempt in range(3):
            try:
                df = yf.download(ticker, start, end, progress=False)
                if df is not None and not df.empty:
                    break
            except Exception as e:
                logger.warning("yfinance attempt %d failed for %s: %s", attempt + 1, ticker, e)
                if attempt == 2:
                    raise
        if df is None or df.empty:
            raise ValueError("No data found for the given ticker.")

        # yfinance >=0.2.40 returns MultiIndex columns for single tickers;
        # flatten them so df.Close is a plain Series (matching the model pipeline)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()

        # 100 Days moving average
        ma100 = df.Close.rolling(100).mean()

        # 200 Days moving average
        ma200 = df.Close.rolling(200).mean()

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

        # Model Evaluation
        mse = mean_squared_error(y_test, y_predicted)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_predicted)

        # Prepare historical dates as ISO strings for frontend charting
        historical_dates = df.Date.dt.strftime("%Y-%m-%d").tolist()
        historical_prices = df.Close.tolist()
        ma100_list = ma100.tolist()
        ma200_list = ma200.tolist()

        # Test period indices (0-based for the prediction chart x-axis)
        test_indices = list(range(len(y_test)))

        return {
            'status': 'success',
            'historical_prices': historical_prices,
            'historical_dates': historical_dates,
            'ma100': ma100_list,
            'ma200': ma200_list,
            'y_test': y_test.tolist(),
            'y_predicted': y_predicted.tolist(),
            'test_indices': test_indices,
            'mse': float(mse),
            'rmse': float(rmse),
            'r2': float(r2),
        }