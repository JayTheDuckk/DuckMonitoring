import React, { useEffect, useState, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import api from '../../services/api';
import { useNavigate } from 'react-router-dom';

const TopologyGraph = () => {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const navigate = useNavigate();
    const fgRef = useRef();

    useEffect(() => {
        const fetchTopology = async () => {
            try {
                const response = await api.get('/topology/graph/');
                setGraphData(response.data);
            } catch (error) {
                console.error("Error fetching topology:", error);
            }
        };

        fetchTopology();
    }, []);

    const handleNodeClick = (node) => {
        if (node.type === 'host') {
            console.log("Clicked host:", node);
            navigate(`/host/${node.id}`);
        }
    };

    if (graphData.nodes.length === 0) {
        return (
            <div style={{
                height: '80vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                background: 'var(--bg-card)',
                color: 'var(--text-secondary)'
            }}>
                <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🕸️</div>
                <h3>No Topology Data</h3>
                <p>No hosts or connections found to display.</p>
            </div>
        );
    }

    return (
        <div style={{
            padding: '1.5rem',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-sm)',
            height: 'calc(100vh - 140px)',
            display: 'flex',
            flexDirection: 'column'
        }}>
            <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Network Topology</h2>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    {graphData.nodes.length} Nodes • {graphData.links.length} Links
                </div>
            </div>

            <div style={{ flex: 1, border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden', position: 'relative' }}>
                <ForceGraph2D
                    ref={fgRef}
                    graphData={graphData}
                    nodeLabel="id"
                    nodeRelSize={6}
                    nodeCanvasObject={(node, ctx, globalScale) => {
                        const label = node.display_name || node.id;
                        const fontSize = 12 / globalScale;
                        ctx.font = `${fontSize}px Sans-Serif`;
                        const textWidth = ctx.measureText(label).width;
                        const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // some padding

                        // Node color based on status
                        let fill = '#ecc94b';
                        if (node.status === 'up') fill = '#48bb78';
                        if (node.status === 'down') fill = '#f56565';
                        if (node.type === 'unknown') fill = '#a0aec0';

                        // Draw Node
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
                        ctx.fillStyle = fill;
                        ctx.fill();

                        // Draw Label
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillStyle = 'var(--text-primary)';
                        // Since custom rendering overrides default, we need to handle color manually or use getComputedStyle
                        // For simplicity, let's use a dark gray/white depending on theme, or just black for now
                        ctx.fillStyle = '#718096'; // var(--text-secondary)
                        ctx.fillText(label, node.x, node.y + 8);

                        node.__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
                    }}
                    nodePointerAreaPaint={(node, color, ctx) => {
                        ctx.fillStyle = color;
                        const bckgDimensions = node.__bckgDimensions;
                        bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
                    }}
                    linkColor={() => '#cbd5e0'}
                    linkWidth={2}
                    onNodeClick={handleNodeClick}
                    cooldownTicks={100}
                    onEngineStop={() => fgRef.current.zoomToFit(400)}
                />
            </div>
        </div>
    );
};

export default TopologyGraph;
