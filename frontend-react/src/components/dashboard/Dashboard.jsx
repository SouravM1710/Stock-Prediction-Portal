import React, { useEffect, useState, useMemo } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faSpinner } from '@fortawesome/free-solid-svg-icons'

import axiosInstance from '../../axiosInstance';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// Free-tier hosts (Render) cold-start the TensorFlow model on the first
// predict after idle, which can fail once. Only these conditions are worth
// one retry — anything else (4xx, auth) should surface immediately.
const isTransientError = (error) => {
    if (!error.response) return true; // network error / timeout / no response
    return [500, 502, 503, 504].includes(error.response.status);
};

const Dashboard = () => {

    const [ticker, setTicker] = useState('')
    const [error, setError] = useState()
    const [loading, setLoading] = useState(false)
    const [chartData, setChartData] = useState(null)

    useEffect(()=>{
        const fetchProtectedData = async () =>{
            try {
                await axiosInstance.get('/protected-view/' );
            } catch (error) {
                console.error("Error fetching protected data:", error);
            }
        }
        fetchProtectedData();
    },[])

    // Prepare data for historical price chart (Close + MA100 + MA200)
    const historicalChartData = useMemo(() => {
        if (!chartData) return [];
        const { historical_prices, historical_dates, ma100, ma200 } = chartData;
        return historical_prices.map((price, i) => ({
            date: historical_dates[i],
            price: price,
            ma100: ma100[i],
            ma200: ma200[i],
        })).filter(d => d.price !== null && !isNaN(d.price));
    }, [chartData]);

    // Prepare data for prediction chart (Actual vs Predicted)
    const predictionChartData = useMemo(() => {
        if (!chartData) return [];
        const { y_test, y_predicted, test_indices } = chartData;
        return y_test.map((actual, i) => ({
            index: test_indices[i],
            actual: actual,
            predicted: y_predicted[i],
        }));
    }, [chartData]);

    const handleSubmit = async (e) =>{
        e.preventDefault();
        setLoading(true)
        setError(null)
        setChartData(null)
        try {
            const callPredict = () => axiosInstance.post('/predict/',{ ticker: ticker })
            let response
            try {
                response = await callPredict()
            } catch (err) {
                if (isTransientError(err)) {
                    response = await callPredict() // retry once for cold-start flakiness
                } else {
                    throw err
                }
            }
            console.log(response.data)

            if(response.data.error){
                setError(response.data.error)
            } else {
                setChartData(response.data)
            }
        } catch (error) {
            console.error("Prediction failed:", error);
            setError(error.response?.data?.error || "Prediction failed. Please try again.");
        }finally{
            setLoading(false)
        }
    }

  return (
    <div className='container'>
        <div className="row">
            <div className="col-md-6 mx-auto">
                <form onSubmit={handleSubmit}>
                    <input type="text" className="form-control" placeholder='Enter Stock Ticker' onChange={(e)=> setTicker(e.target.value)} required/>
                    <small>{error && <div className='text-danger'>{error}</div>}</small>
                    <button className="btn btn-info mt-3">{loading ? <span><FontAwesomeIcon icon={faSpinner} spin/>Please wait...</span>: 'See Prediction'}</button>
                </form>
            </div>

            {/* Historical Price Chart with Moving Averages */}
            {chartData && historicalChartData.length > 0 && (
                <div className="prediction mt-5">
                    <div className="p-3">
                        <h4 className="text-light mb-3">{ticker.toUpperCase()} — Historical Price & Moving Averages</h4>
                        <div style={{ width: '100%', height: 400 }}>
                            <ResponsiveContainer>
                                <LineChart data={historicalChartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fill: '#aaa', fontSize: 11 }}
                                        tickLine={{ stroke: '#444' }}
                                        axisLine={{ stroke: '#444' }}
                                        interval="preserveStartEnd"
                                    />
                                    <YAxis
                                        tick={{ fill: '#aaa', fontSize: 11 }}
                                        tickLine={{ stroke: '#444' }}
                                        axisLine={{ stroke: '#444' }}
                                        tickFormatter={(value) => `$${value.toFixed(2)}`}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e1e1e', border: '1px solid #333', borderRadius: '4px' }}
                                        labelStyle={{ color: '#fff' }}
                                        formatter={(value) => [`$${value.toFixed(2)}`, 'Price']}
                                    />
                                    <Legend wrapperStyle={{ color: '#fff', paddingTop: '10px' }} />
                                    <Line
                                        type="monotone"
                                        dataKey="price"
                                        stroke="#00d4aa"
                                        strokeWidth={1.5}
                                        dot={false}
                                        name="Closing Price"
                                        activeDot={{ r: 4, strokeWidth: 2 }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="ma100"
                                        stroke="#ff6b6b"
                                        strokeWidth={1}
                                        dot={false}
                                        name="100-Day MA"
                                        activeDot={{ r: 4, strokeWidth: 2 }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="ma200"
                                        stroke="#4ecdc4"
                                        strokeWidth={1}
                                        dot={false}
                                        name="200-Day MA"
                                        activeDot={{ r: 4, strokeWidth: 2 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Actual vs Predicted Chart */}
                    <div className="p-3">
                        <h4 className="text-light mb-3">Prediction vs Actual (Test Period)</h4>
                        <div style={{ width: '100%', height: 400 }}>
                            <ResponsiveContainer>
                                <LineChart data={predictionChartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                    <XAxis
                                        dataKey="index"
                                        tick={{ fill: '#aaa', fontSize: 11 }}
                                        tickLine={{ stroke: '#444' }}
                                        axisLine={{ stroke: '#444' }}
                                        label={{ value: 'Days (Test Period)', position: 'insideBottom', offset: -10, fill: '#888' }}
                                    />
                                    <YAxis
                                        tick={{ fill: '#aaa', fontSize: 11 }}
                                        tickLine={{ stroke: '#444' }}
                                        axisLine={{ stroke: '#444' }}
                                        tickFormatter={(value) => `$${value.toFixed(2)}`}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e1e1e', border: '1px solid #333', borderRadius: '4px' }}
                                        labelStyle={{ color: '#fff' }}
                                        labelFormatter={(label) => `Day ${label}`}
                                        formatter={(value, name) => [`$${value.toFixed(2)}`, name]}
                                    />
                                    <Legend wrapperStyle={{ color: '#fff', paddingTop: '10px' }} />
                                    <Line
                                        type="monotone"
                                        dataKey="actual"
                                        stroke="#00d4aa"
                                        strokeWidth={1.5}
                                        dot={false}
                                        name="Actual Price"
                                        activeDot={{ r: 4, strokeWidth: 2 }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="predicted"
                                        stroke="#ff6b6b"
                                        strokeWidth={1.5}
                                        dot={false}
                                        name="Predicted Price"
                                        activeDot={{ r: 4, strokeWidth: 2 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Model Evaluation Metrics */}
                    <div className="text-light p-3">
                        <h4 className="mb-3">Model Evaluation</h4>
                        <div className="row">
                            <div className="col-md-4">
                                <div className="bg-dark p-3 rounded text-center">
                                    <div className="text-muted small">MSE</div>
                                    <div className="fs-4 fw-bold">{chartData.mse ? chartData.mse.toFixed(4) : '—'}</div>
                                </div>
                            </div>
                            <div className="col-md-4">
                                <div className="bg-dark p-3 rounded text-center">
                                    <div className="text-muted small">RMSE</div>
                                    <div className="fs-4 fw-bold">{chartData.rmse ? chartData.rmse.toFixed(4) : '—'}</div>
                                </div>
                            </div>
                            <div className="col-md-4">
                                <div className="bg-dark p-3 rounded text-center">
                                    <div className="text-muted small">R²</div>
                                    <div className="fs-4 fw-bold">{chartData.r2 !== undefined ? chartData.r2.toFixed(4) : '—'}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    </div>
  )
}

export default Dashboard