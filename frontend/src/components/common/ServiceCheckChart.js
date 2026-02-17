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
import { getServiceCheckHistory } from '../../services/api';
import { format } from 'date-fns';
import './ServiceCheckChart.css';

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

const ServiceCheckChart = ({ checkId, checkName, checkType, hours = 24, forceRefresh }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadCheckHistory = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Add cache-busting parameter to ensure fresh data
      const cacheBuster = Date.now();
      const response = await getServiceCheckHistory(checkId, { hours, _t: cacheBuster });
      
      // Handle different response formats (array, paginated, or object)
      const results = Array.isArray(response.data) 
        ? response.data 
        : response.data.results || response.data.data || [];
      
      if (!results || results.length === 0) {
        setData(null);
        setError(null); // Don't show error for empty data, just show empty state
        setLoading(false);
        return;
      }

      // Sort by timestamp
      results.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

      const labels = results.map(r => format(new Date(r.timestamp), 'MMM dd HH:mm'));
      const responseTimes = results.map(r => r.response_time || null);
      const statuses = results.map(r => r.status);

      // Create datasets for response time and status
      const datasets = [];

      // Response time dataset
      if (responseTimes.some(rt => rt !== null)) {
        datasets.push({
          label: 'Response Time (ms)',
          data: responseTimes,
          borderColor: getColorForCheckType(checkType),
          backgroundColor: getColorForCheckType(checkType, 0.1),
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 2,
          pointHoverRadius: 5,
          yAxisID: 'y',
        });
      }

      // Status dataset (as 0/1 for ok/critical)
      datasets.push({
        label: 'Status (OK=1, Critical=0)',
        data: statuses.map(s => s === 'ok' ? 1 : (s === 'critical' ? 0 : 0.5)),
        borderColor: statuses.map(s => getStatusColor(s)),
        backgroundColor: statuses.map(s => getStatusColor(s, 0.2)),
        borderWidth: 2,
        fill: false,
        tension: 0,
        pointRadius: 3,
        pointHoverRadius: 6,
        yAxisID: 'y1',
        stepped: 'after',
      });

      const chartData = {
        labels,
        datasets,
      };

      setData(chartData);
      setError(null);
    } catch (err) {
      setError('Failed to load check history');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [checkId, checkType, hours]);

  // Separate effect to handle forceRefresh changes
  useEffect(() => {
    if (forceRefresh !== undefined) {
      // Force clear and reload when forceRefresh changes
      setData(null);
      setError(null);
      setLoading(true);
      loadCheckHistory();
    }
  }, [forceRefresh, loadCheckHistory]);

  useEffect(() => {
    // Clear data immediately when component mounts or key changes
    setData(null);
    setError(null);
    setLoading(true);
    
    loadCheckHistory();
    const interval = setInterval(loadCheckHistory, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [checkId, hours, loadCheckHistory]);

  const getColorForCheckType = (type, alpha = 1) => {
    const colors = {
      ping: `rgba(102, 126, 234, ${alpha})`,
      ssh: `rgba(118, 75, 162, ${alpha})`,
      http: `rgba(33, 150, 243, ${alpha})`,
      https: `rgba(76, 175, 80, ${alpha})`,
      tcp: `rgba(255, 152, 0, ${alpha})`,
      udp: `rgba(156, 39, 176, ${alpha})`,
      dns: `rgba(0, 188, 212, ${alpha})`,
    };
    return colors[type] || `rgba(158, 158, 158, ${alpha})`;
  };

  const getStatusColor = (status, alpha = 1) => {
    switch (status) {
      case 'ok':
        return `rgba(76, 175, 80, ${alpha})`;
      case 'warning':
        return `rgba(255, 152, 0, ${alpha})`;
      case 'critical':
        return `rgba(244, 67, 54, ${alpha})`;
      default:
        return `rgba(158, 158, 158, ${alpha})`;
    }
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
          label: function(context) {
            if (context.datasetIndex === 0) {
              // Response time
              return context.parsed.y !== null 
                ? `Response Time: ${context.parsed.y.toFixed(2)} ms`
                : 'Response Time: N/A';
            } else {
              // Status
              const status = context.raw === 1 ? 'OK' : (context.raw === 0 ? 'Critical' : 'Unknown');
              return `Status: ${status}`;
            }
          }
        }
      },
      title: {
        display: true,
        text: `${checkName} - Historical Data`,
        font: {
          size: 16
        }
      }
    },
    scales: {
      y: {
        type: 'linear',
        position: 'left',
        beginAtZero: true,
        title: {
          display: true,
          text: 'Response Time (ms)',
        },
      },
      y1: {
        type: 'linear',
        position: 'right',
        min: 0,
        max: 1,
        title: {
          display: true,
          text: 'Status',
        },
        ticks: {
          stepSize: 1,
          callback: function(value) {
            return value === 1 ? 'OK' : (value === 0 ? 'Critical' : 'Unknown');
          }
        },
        grid: {
          drawOnChartArea: false,
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
    return <div className="chart-empty">No historical data available for this time range</div>;
  }

  // Use a unique key that changes when we want to force remount
  const chartKey = `chart-${checkId}-${hours}`;

  return (
    <div className="service-check-chart">
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
          <div className="chart-empty">No historical data available for this time range</div>
        )}
      </div>
    </div>
  );
};

export default ServiceCheckChart;

