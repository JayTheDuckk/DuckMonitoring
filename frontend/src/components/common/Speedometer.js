import React, { useState, useEffect, useCallback } from 'react';
import { getMetricsSummary } from '../../services/api';
import './Speedometer.css';

const Speedometer = ({ hostId, hostname }) => {
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadMetrics = useCallback(async () => {
    try {
      setError(null);
      const response = await getMetricsSummary(hostId, { hours: 1, _t: Date.now() });
      const metricsData = response.data;
      
      // Transform into a map for easy access
      const metricsMap = {};
      metricsData.forEach(metric => {
        metricsMap[metric.name] = metric;
      });
      
      setMetrics(metricsMap);
      setLoading(false);
    } catch (err) {
      setError('Failed to load metrics');
      console.error(err);
      setLoading(false);
    }
  }, [hostId]);

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, [loadMetrics]);

  const getMetricValue = (metricName) => {
    const metric = metrics[metricName];
    if (!metric) return null;
    
    // Ensure value is between 0 and 100 for percentage metrics
    let value = metric.latest_value;
    if (metric.unit === '%') {
      value = Math.max(0, Math.min(100, value));
    }
    return value;
  };

  if (loading && Object.keys(metrics).length === 0) {
    return <div className="speedometer-loading">Loading metrics...</div>;
  }

  if (error && Object.keys(metrics).length === 0) {
    return <div className="speedometer-error">{error}</div>;
  }

  // Find percentage-based metrics
  // Check various possible metric name formats
  const cpuUsage = getMetricValue('cpu.usage') || getMetricValue('CPU Usage');
  const memoryUsage = getMetricValue('memory.usage') || getMetricValue('Memory Usage');
  const diskUsage = getMetricValue('disk.usage') || getMetricValue('Disk Usage');

  const gauges = [];
  
  if (cpuUsage !== null) {
    gauges.push({ name: 'CPU Usage', value: cpuUsage, color: '#4D9CFF' });
  }
  if (memoryUsage !== null) {
    gauges.push({ name: 'Memory Usage', value: memoryUsage, color: '#906BFF' });
  }
  if (diskUsage !== null) {
    gauges.push({ name: 'Disk Usage', value: diskUsage, color: '#f093fb' });
  }

  // Also check for disk usage on specific partitions
  // Only show the root/main partition as "Disk Usage", skip all others including boot/efi
  Object.keys(metrics).forEach(key => {
    const metric = metrics[key];
    if (metric.unit === '%') {
      // Skip if we already added this metric
      if (key === 'cpu.usage' || key === 'CPU Usage' || 
          key === 'memory.usage' || key === 'Memory Usage' ||
          key === 'disk.usage' || key === 'Disk Usage') {
        return;
      }
      
      // Skip individual CPU core metrics (only show overall CPU usage)
      if (key.startsWith('cpu.core.') || key.startsWith('CPU Core ')) {
        return;
      }
      
      // Only process disk metrics
      if (key.startsWith('disk.')) {
        // Extract partition path
        const partitionPath = key.replace('disk.', '').replace('.usage', '').replace(/_/g, '/');
        
        // Skip boot/efi partitions
        if (partitionPath.includes('boot') || partitionPath.includes('efi') || partitionPath.includes('EFI')) {
          return;
        }
        
        // Only show the root partition (/) as "Disk Usage"
        if (partitionPath === '/' || partitionPath === '') {
          const value = getMetricValue(key);
          if (value !== null) {
            gauges.push({ 
              name: 'Disk Usage', 
              value: value, 
              color: '#4facfe' 
            });
          }
        }
        // Skip all other partitions
        return;
      }
    }
  });

  if (gauges.length === 0) {
    return (
      <div className="speedometer-empty">
        No percentage-based metrics available. Make sure the agent is running and sending data.
      </div>
    );
  }

  return (
    <div className="speedometer-container">
      <div className="speedometer-header">
        <h3>Real-Time Usage Gauges</h3>
      </div>
      <div className="speedometer-grid">
        {gauges.map(gauge => (
          <SpeedometerGauge
            key={gauge.name}
            label={gauge.name}
            value={gauge.value}
            color={gauge.color}
          />
        ))}
      </div>
    </div>
  );
};

const SpeedometerGauge = ({ label, value, color }) => {
  // Calculate angle for needle (0-180 degrees, where 0 is left, 180 is right)
  // 0% = -90 degrees, 50% = 0 degrees, 100% = 90 degrees
  const angle = (value / 100) * 180 - 90;
  
  // Color zones
  const getZoneColor = (val) => {
    if (val < 50) return '#4caf50'; // Green
    if (val < 80) return '#ff9800'; // Orange
    return '#f44336'; // Red
  };

  const zoneColor = getZoneColor(value);

  return (
    <div className="speedometer-gauge">
      <div className="gauge-label">{label}</div>
      <div className="gauge-wrapper">
        <svg
          className="gauge-svg"
          viewBox="0 0 200 120"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Background arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="var(--border-color)"
            strokeWidth="12"
            strokeLinecap="round"
          />
          
          {/* Colored arc based on value */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={zoneColor}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${(value / 100) * 251.2} 251.2`}
            className="gauge-arc"
          />
          
          {/* Tick marks */}
          {[0, 25, 50, 75, 100].map((tick) => {
            const tickAngle = (tick / 100) * 180 - 90;
            const rad = (tickAngle * Math.PI) / 180;
            const x1 = 100 + 70 * Math.cos(rad);
            const y1 = 100 + 70 * Math.sin(rad);
            const x2 = 100 + 80 * Math.cos(rad);
            const y2 = 100 + 80 * Math.sin(rad);
            return (
              <line
                key={tick}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="var(--text-secondary)"
                strokeWidth="2"
              />
            );
          })}
          
          {/* Tick labels */}
          {[0, 25, 50, 75, 100].map((tick) => {
            const tickAngle = (tick / 100) * 180 - 90;
            const rad = (tickAngle * Math.PI) / 180;
            const x = 100 + 60 * Math.cos(rad);
            const y = 100 + 60 * Math.sin(rad);
            return (
              <text
                key={tick}
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="var(--text-secondary)"
                fontSize="10"
                className="gauge-tick-label"
              >
                {tick}
              </text>
            );
          })}
          
          {/* Needle */}
          <g className="gauge-needle" style={{ transformOrigin: '100px 100px' }}>
            <line
              x1="100"
              y1="100"
              x2="100"
              y2="30"
              stroke={color}
              strokeWidth="3"
              strokeLinecap="round"
              transform={`rotate(${angle} 100 100)`}
            />
            <circle
              cx="100"
              cy="100"
              r="5"
              fill={color}
            />
          </g>
        </svg>
      </div>
      <div className="gauge-value" style={{ color: zoneColor }}>
        {value.toFixed(1)}%
      </div>
    </div>
  );
};

export default Speedometer;

