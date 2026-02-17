import React, { useState, useEffect, useCallback } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { getHostMetrics, getUPSMetrics, getSNMPDeviceMetrics } from '../../services/api';
import { format } from 'date-fns';
import './MetricChart.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const MetricChart = ({ hostId, metricName, metricType, unit, hours, forceRefresh, isUPS = false, isSNMP = false, color }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadMetricData = useCallback(async () => {
    try {
      setLoading(true);

      // Add cache-busting parameter to ensure fresh data
      const cacheBuster = Date.now();
      let response;
      if (isUPS) {
        response = await getUPSMetrics(hostId, {
          metric_name: metricName,
          hours: hours,
          _t: cacheBuster
        });
      } else if (isSNMP) {
        response = await getSNMPDeviceMetrics(hostId, {
          metric_name: metricName,
          hours: hours,
          _t: cacheBuster
        });
      } else {
        response = await getHostMetrics(hostId, {
          metric_name: metricName,
          hours: hours,
          _t: cacheBuster
        });
      }

      const metrics = Array.isArray(response.data) ? response.data : response.data.results || [];

      if (metrics.length === 0) {
        setData(null);
        setError(null); // Don't show error for empty data
        setLoading(false);
        return;
      }

      // Sort by timestamp
      metrics.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

      // Handle both numeric values and value_string for SNMP devices
      const processedMetrics = metrics.map(m => {
        let value = m.value;
        if (isSNMP && value === null && m.value_string) {
          // Try to parse string value as number
          const parsed = parseFloat(m.value_string);
          value = isNaN(parsed) ? null : parsed;
        }
        return {
          timestamp: m.timestamp,
          value: value
        };
      }).filter(m => m.value !== null && m.value !== undefined); // Filter out null/undefined values

      if (processedMetrics.length === 0) {
        setData(null);
        setError(null);
        setLoading(false);
        return;
      }

      const labels = processedMetrics.map(m => format(new Date(m.timestamp), 'MMM dd HH:mm'));
      const values = processedMetrics.map(m => m.value);

      const borderColor = color || getColorForMetricType(metricType);
      const backgroundColor = color ? `${color}33` : getColorForMetricType(metricType, 0.1);

      const chartData = {
        labels,
        datasets: [
          {
            label: `${metricName} (${unit || ''})`,
            data: values,
            borderColor: borderColor,
            backgroundColor: backgroundColor,
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 5,
          },
        ],
      };

      setData(chartData);
      setError(null);
    } catch (err) {
      setError('Failed to load metric data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [hostId, metricName, metricType, unit, hours, isUPS, isSNMP]);

  // Separate effect to handle forceRefresh changes
  useEffect(() => {
    if (forceRefresh !== undefined) {
      // Force clear and reload when forceRefresh changes
      setData(null);
      setError(null);
      setLoading(true);
      loadMetricData();
    }
  }, [forceRefresh, loadMetricData]);

  useEffect(() => {
    // Clear data immediately when component mounts or key changes
    setData(null);
    setError(null);
    setLoading(true);

    loadMetricData();
    const interval = setInterval(loadMetricData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [hostId, metricName, hours, loadMetricData]);

  const getColorForMetricType = (type, alpha = 1) => {
    const colors = {
      cpu: `rgba(102, 126, 234, ${alpha})`,
      memory: `rgba(118, 75, 162, ${alpha})`,
      disk: `rgba(255, 152, 0, ${alpha})`,
      network: `rgba(33, 150, 243, ${alpha})`,
    };
    return colors[type] || `rgba(158, 158, 158, ${alpha})`;
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: function (context) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
          }
        }
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: unit ? `Value (${unit})` : 'Value',
        },
      },
      x: {
        title: {
          display: true,
          text: 'Time',
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
        },
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  };

  if (loading) {
    return <div className="chart-loading">Loading chart data...</div>;
  }

  if (error) {
    return <div className="chart-error">{error}</div>;
  }

  if (!data) {
    return <div className="chart-error">No data available</div>;
  }

  // Use a unique key that changes when we want to force remount
  const chartKey = `chart-${hostId}-${metricName}-${hours}`;

  return (
    <div className="metric-chart">
      <div className="chart-wrapper">
        {data ? (
          <Line
            key={chartKey}
            data={data}
            options={{
              ...chartOptions,
              animation: {
                duration: 0 // Disable animation to prevent stale data display
              }
            }}
            updateMode="none"
          />
        ) : (
          <div className="chart-empty">No data available for this time range</div>
        )}
      </div>
    </div>
  );
};

export default MetricChart;

