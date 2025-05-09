import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';

function Graph() {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [rawConnectionsData, setRawConnectionsData] = useState(null);
    const [includeFuzzy, setIncludeFuzzy] = useState(true);
    const [loading, setLoading] = useState(false);
    const svgRef = useRef();
    const [showSecondDegree, setShowSecondDegree] = useState(false); 
    const [showThirdDegree, setShowThirdDegree] = useState(false);
    const [selectedPaper, setSelectedPaper] = useState(null);

    // Function to convert connections data to graph format
    const processGraphData = (data, includeFuzzyConnections = true) => {
        if (!data) return { nodes: [], links: [] };
        
        console.log("DEBUG: Processing graph data:", data);
        
        const nodes = [];
        const links = [];
        const nodeSet = new Set();

        // Process first degree connections
        if (data.first_degree) {
            // Add source node (the main paper)
            const sourceId = data.first_degree.source_id;
            const sourceTitle = data.first_degree.source_title || 'Source Paper';
            
            nodes.push({
                id: sourceId,
                name: sourceTitle,
                val: 20,
                color: '#ff0000', // Red for source paper
                level: 0
            });
            nodeSet.add(sourceId);

            // Add first degree connections
            if (data.first_degree.connections && Array.isArray(data.first_degree.connections)) {
                console.log("DEBUG: Processing connections:", data.first_degree.connections);
                data.first_degree.connections.forEach(conn => {
                    console.log("DEBUG: Processing connection:", conn);
                    // Handle both string IDs and object-based connections
                    const connId = typeof conn === 'string' ? conn : conn.id;
                    
                    // For paper titles, ensure we have a meaningful title instead of just "Paper ID"
                    let connTitle;
                    if (typeof conn === 'object' && conn.title) {
                        connTitle = conn.title;
                    } else if (typeof conn === 'string') {
                        // We'll fetch titles later for these nodes
                        connTitle = `Loading title for ${conn}...`;
                    } else {
                        connTitle = `Paper ${connId}`;
                    }
                    
                    // Check for similarity property to identify embedding-based connections
                    const hasSimilarity = typeof conn === 'object' && conn.similarity !== undefined;
                    const isFuzzy = hasSimilarity;
                    
                    console.log(`DEBUG: Connection ${connId} - isFuzzy: ${isFuzzy}, similarity: ${hasSimilarity ? conn.similarity : 'N/A'}`);
                    
                    // Skip fuzzy connections if not included
                    if (!includeFuzzyConnections && isFuzzy) {
                        console.log(`DEBUG: Skipping fuzzy connection: ${connId}`);
                        return;
                    }
                    
                    if (!nodeSet.has(connId)) {
                        nodes.push({
                            id: connId,
                            name: connTitle,
                            val: 10,
                            color: isFuzzy ? '#9900cc' : '#0000ff', // Purple for embedding-based, Blue for citation-based
                            level: 1,
                            isFuzzy: isFuzzy
                        });
                        nodeSet.add(connId);
                        console.log(`DEBUG: Added node: ${connId}, isFuzzy: ${isFuzzy}`);
                    }
                    
                    links.push({
                        source: sourceId,
                        target: connId,
                        value: isFuzzy ? conn.similarity : 1,
                        isFuzzy: isFuzzy
                    });
                    console.log(`DEBUG: Added link: ${sourceId} -> ${connId}, isFuzzy: ${isFuzzy}`);
                });
            }
        }

        // Process second degree connections only if checkbox is checked
        if (data.second_degree && showSecondDegree) {
            // Handle both array format and object format
            const processSecondDegreeConnections = (sourceId, connections) => {
                if (nodeSet.has(sourceId) && Array.isArray(connections)) {
                    connections.forEach(conn => {
                        // Handle both string IDs and object-based connections
                        const connId = typeof conn === 'string' ? conn : conn.id;
                        
                        // For paper titles, ensure we have a meaningful title
                        let connTitle;
                        if (typeof conn === 'object' && conn.title) {
                            connTitle = conn.title;
                        } else if (typeof conn === 'string') {
                            // We'll fetch titles later for these nodes
                            connTitle = `Loading title for ${conn}...`;
                        } else {
                            connTitle = `Paper ${connId}`;
                        }
                        
                        const isFuzzy = typeof conn === 'object' && !!conn.similarity;
                        
                        // Skip fuzzy connections in 2nd degree - only use citation-based for 2nd degree
                        if (isFuzzy) {
                            return;
                        }
                        
                        if (!nodeSet.has(connId)) {
                            nodes.push({
                                id: connId,
                                name: connTitle,
                                val: 5,
                                color: '#00ff00', // Green for citation-based 2nd degree
                                level: 2,
                                isFuzzy: false
                            });
                            nodeSet.add(connId);
                        }
                        
                        links.push({
                            source: sourceId,
                            target: connId,
                            value: 0.5,
                            isFuzzy: false
                        });
                    });
                }
            };
            
            // Check if second_degree is an array (old format) or object (new format)
            if (Array.isArray(data.second_degree)) {
                // Old format: array of objects with source_id and connections
                data.second_degree.forEach(item => {
                    if (item && item.source_id && Array.isArray(item.connections)) {
                        processSecondDegreeConnections(item.source_id, item.connections);
                    }
                });
            } else {
                // New format: object with keys as source_ids and values as connection arrays
                Object.entries(data.second_degree).forEach(([sourceId, connections]) => {
                    processSecondDegreeConnections(sourceId, connections);
                });
            }
        }

        // Process third degree connections only if checkbox is checked
        if (data.third_degree && showThirdDegree) {
            // Handle both array format and object format
            const processThirdDegreeConnections = (sourceId, connections) => {
                if (nodeSet.has(sourceId) && Array.isArray(connections)) {
                    connections.forEach(conn => {
                        // Handle both string IDs and object-based connections
                        const connId = typeof conn === 'string' ? conn : conn.id;
                        
                        // For paper titles, ensure we have a meaningful title
                        let connTitle;
                        if (typeof conn === 'object' && conn.title) {
                            connTitle = conn.title;
                        } else if (typeof conn === 'string') {
                            // We'll fetch titles later for these nodes
                            connTitle = `Loading title for ${conn}...`;
                        } else {
                            connTitle = `Paper ${connId}`;
                        }
                        
                        const isFuzzy = typeof conn === 'object' && !!conn.similarity;
                        
                        // Skip fuzzy connections in 3rd degree - only use citation-based for 3rd degree
                        if (isFuzzy) {
                            return;
                        }
                        
                        if (!nodeSet.has(connId)) {
                            nodes.push({
                                id: connId,
                                name: connTitle,
                                val: 2,
                                color: '#ffff00', // Yellow for citation-based 3rd degree
                                level: 3,
                                isFuzzy: false
                            });
                            nodeSet.add(connId);
                        }
                        
                        links.push({
                            source: sourceId,
                            target: connId,
                            value: 0.2,
                            isFuzzy: false
                        });
                    });
                }
            };
            
            // Check if third_degree is an array (old format) or object (new format)
            if (Array.isArray(data.third_degree)) {
                // Old format: array of objects with source_id and connections
                data.third_degree.forEach(item => {
                    if (item && item.source_id && Array.isArray(item.connections)) {
                        processThirdDegreeConnections(item.source_id, item.connections);
                    }
                });
            } else {
                // New format: object with keys as source_ids and values as connection arrays
                Object.entries(data.third_degree).forEach(([sourceId, connections]) => {
                    processThirdDegreeConnections(sourceId, connections);
                });
            }
        }

        console.log("DEBUG: Processed graph data:", { nodes: nodes.length, links: links.length });
        return { nodes, links };
    };

    // D3 Graph Rendering
    const renderD3Graph = (data) => {
        const width = 800;
        const height = 600;

        // Clear previous SVG
        d3.select(svgRef.current).selectAll("*").remove();
        
        // Create SVG
        const svg = d3.select(svgRef.current)
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [0, 0, width, height])
            .attr("style", "max-width: 100%; height: auto;");
            
        // Add zoom and pan capabilities
        const g = svg.append("g");
        
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });
            
        svg.call(zoom);
            
        // Create simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(width / 2, height / 2));
            
        // Create the links
        const link = g.append("g")
            .selectAll("line")
            .data(data.links)
            .join("line")
            .attr("stroke", d => d.isFuzzy ? "#9900cc" : "#999") // Purple for fuzzy/embedding connections
            .attr("stroke-opacity", d => d.isFuzzy ? 0.8 : 0.6)  // More visible opacity for embedding connections
            .attr("stroke-width", d => {
                // Make embedding connections thicker based on similarity
                if (d.isFuzzy) {
                    // Scale similarity (0-1) to width (2-6)
                    return Math.max(2, Math.min(6, d.value * 6));
                } else {
                    return Math.sqrt(d.value) * 2;
                }
            })
            .attr("stroke-dasharray", d => d.isFuzzy ? "5,5" : "none");
            
        // Create a group for each node
        const node = g.append("g")
            .selectAll("g")
            .data(data.nodes)
            .join("g")
            .call(drag(simulation))
            .on("click", (event, d) => {
                // Handle node click - display paper info
                console.log("Fetching details for paper:", d.id);
                
                // First set basic info immediately
                setSelectedPaper({
                    id: d.id,
                    name: d.name,
                    level: d.level,
                    isFuzzy: d.isFuzzy,
                    abstract: "Loading...",
                    isLoading: true
                });
                
                // Then fetch full paper details including abstract
                fetch(`http://localhost:8080/api/paper/${d.id}`)
                    .then(response => {
                        if (!response.ok) {
                            console.error(`Error response from server: ${response.status}`);
                            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log("Received paper details:", data);
                        if (data.success) {
                            setSelectedPaper(prevState => ({
                                ...prevState,
                                name: data.title || prevState.name,
                                abstract: data.abstract || "No abstract available",
                                authors: data.authors,
                                categories: data.categories,
                                year: data.year,
                                isLoading: false
                            }));
                        } else {
                            throw new Error(data.error || 'Unknown error');
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching paper details:', error);
                        // Fall back to search API if paper endpoint fails
                        fetch(`http://localhost:8080/api/search?q=${encodeURIComponent(d.id)}`)
                            .then(response => response.json())
                            .then(data => {
                                if (data.success && data.results && data.results.length > 0) {
                                    const paperData = data.results[0];
                                    setSelectedPaper(prevState => ({
                                        ...prevState,
                                        name: paperData.title || prevState.name,
                                        abstract: paperData.abstract || "No abstract available",
                                        authors: paperData.authors,
                                        categories: paperData.categories,
                                        year: paperData.year,
                                        isLoading: false
                                    }));
                                } else {
                                    setSelectedPaper(prevState => ({
                                        ...prevState,
                                        abstract: "Unable to load abstract. Paper may not be in the database.",
                                        isLoading: false
                                    }));
                                }
                            })
                            .catch(searchError => {
                                console.error('Error with fallback search:', searchError);
                                setSelectedPaper(prevState => ({
                                    ...prevState,
                                    abstract: "Unable to load abstract. Try searching for this paper ID directly.",
                                    isLoading: false
                                }));
                            });
                    });
                
                // Stop event propagation to prevent zoom/pan when clicking node
                event.stopPropagation();
            });
            
        // Add a circle to each node group
        node.append("circle")
            .attr("r", d => Math.sqrt(d.val) * 3)
            .attr("fill", d => d.color);
            
        // Add text label to each node
        node.append("text")
            .text(d => {
                // Truncate long names to reasonable length
                const maxLength = 25;
                return d.name.length > maxLength ? d.name.substring(0, maxLength) + '...' : d.name;
            })
            .attr("x", 0)
            .attr("y", d => -Math.sqrt(d.val) * 3 - 5)
            .attr("text-anchor", "middle")
            .attr("font-size", "10px")
            .attr("dy", ".35em") // Vertically center text
            .style("pointer-events", "none") // Make sure text doesn't interfere with mouse events
            .style("user-select", "none") // Prevent text selection
            .call(wrap, 100); // Apply text wrapping
        
        // Function to wrap text
        function wrap(text, width) {
            text.each(function() {
                const text = d3.select(this);
                const words = text.text().split(/\s+/).reverse();
                const lineHeight = 1.1; // ems
                const y = text.attr("y");
                const dy = parseFloat(text.attr("dy"));
                
                let word,
                    line = [],
                    lineNumber = 0,
                    tspan = text.text(null).append("tspan")
                                .attr("x", 0)
                                .attr("y", y)
                                .attr("dy", dy + "em");
                
                while (word = words.pop()) {
                    line.push(word);
                    tspan.text(line.join(" "));
                    
                    if (tspan.node().getComputedTextLength() > width) {
                        line.pop();
                        tspan.text(line.join(" "));
                        line = [word];
                        
                        // Limit to max 2 lines
                        lineNumber++;
                        if (lineNumber < 2) {
                            tspan = text.append("tspan")
                                    .attr("x", 0)
                                    .attr("y", y)
                                    .attr("dy", lineNumber * lineHeight + dy + "em")
                                    .text(word);
                        } else {
                            // For 3rd line and beyond, use ellipsis
                            if (tspan.text().slice(-3) !== "...") {
                                tspan.text(tspan.text() + "...");
                            }
                            break;
                        }
                    }
                }
            });
        }
        
        // Update positions on each tick
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
                
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        // Update the legend to accurately reflect all connection types
        const legend = svg.append("g")
            .attr("transform", "translate(20,20)");
            
        // Origin node (source paper)
        legend.append("circle")
            .attr("r", 6)
            .attr("fill", "#ff0000")
            .attr("cx", 10)
            .attr("cy", 10);
            
        legend.append("text")
            .text("Origin paper")
            .attr("x", 25)
            .attr("y", 15)
            .attr("font-size", "12px");
        
        // Citation-based 1st degree
        legend.append("circle")
            .attr("r", 6)
            .attr("fill", "#0000ff")
            .attr("cx", 10)
            .attr("cy", 35);
            
        legend.append("text")
            .text("Citation-based 1st degree")
            .attr("x", 25)
            .attr("y", 40)
            .attr("font-size", "12px");
            
        // Citation-based 2nd degree
        legend.append("circle")
            .attr("r", 6)
            .attr("fill", "#00ff00")
            .attr("cx", 10)
            .attr("cy", 60);
            
        legend.append("text")
            .text("Citation-based 2nd degree")
            .attr("x", 25)
            .attr("y", 65)
            .attr("font-size", "12px");
            
        // Citation-based 3rd degree
        legend.append("circle")
            .attr("r", 6)
            .attr("fill", "#ffff00")
            .attr("cx", 10)
            .attr("cy", 85);
            
        legend.append("text")
            .text("Citation-based 3rd degree")
            .attr("x", 25)
            .attr("y", 90)
            .attr("font-size", "12px");
            
        // Embedding-based (only for 1st degree)
        legend.append("circle")
            .attr("r", 6)
            .attr("fill", "#9900cc")
            .attr("cx", 10)
            .attr("cy", 110);
            
        legend.append("text")
            .text("Embedding-based (1st degree)")
            .attr("x", 25)
            .attr("y", 115)
            .attr("font-size", "12px");
        
        // Drag functionality
        function drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            
            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }
            
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
            
            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
        }

        // After the graph is created, fetch and update titles for any nodes that need them
        const nodesToFetch = data.nodes.filter(n => n.name.startsWith("Loading title for"));
        if (nodesToFetch.length > 0) {
            console.log("DEBUG: Fetching titles for", nodesToFetch.length, "nodes");
            
            // For each node that needs a title, fetch it directly from the papers endpoint
            nodesToFetch.forEach(nodeData => {
                const paperId = nodeData.id;
                fetch(`http://localhost:8080/api/paper/${encodeURIComponent(paperId)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            console.log(`DEBUG: Got title for ${paperId}: ${data.title}`);
                            
                            // Update the node's name in the data
                            nodeData.name = data.title;
                            
                            // Update the text in the SVG
                            const textElement = node.filter(d => d.id === paperId).select("text");
                            if (!textElement.empty()) {
                                // First clear existing text
                                textElement.selectAll("*").remove();
                                
                                // Truncate long names to reasonable length
                                const maxLength = 25;
                                const displayTitle = data.title.length > maxLength ? 
                                    data.title.substring(0, maxLength) + '...' : 
                                    data.title;
                                
                                textElement.text(displayTitle)
                                    .call(wrap, 100);
                            }
                        }
                    })
                    .catch(error => {
                        console.error(`Error fetching title for ${paperId}:`, error);
                    });
            });
        }
    };

    // Update graph when connections checkbox states change
    useEffect(() => {
        if (rawConnectionsData) {
            const processedData = processGraphData(rawConnectionsData, includeFuzzy);
            setGraphData(processedData);
        }
    }, [includeFuzzy, rawConnectionsData, showSecondDegree, showThirdDegree]);

    // Listen for changes in DegreeCheckbox component
    useEffect(() => {
        const handleConnectionsLoaded = (event) => {
            if (event && event.detail) {
                console.log("DEBUG: Received connections data:", event.detail);
                setRawConnectionsData(event.detail);
                const data = processGraphData(event.detail, includeFuzzy);
                setGraphData(data);
            }
        };

        const handleFuzzyConnectionsPreference = (event) => {
            if (event && event.detail) {
                setIncludeFuzzy(event.detail.includeFuzzy);
            }
        };
        
        // Listen for degree checkbox changes
        const handleDegreeCheckboxChange = (event) => {
            if (event && event.detail) {
                setShowSecondDegree(event.detail.showSecondDegree);
                setShowThirdDegree(event.detail.showThirdDegree);
            }
        };

        // Add event listeners
        window.addEventListener('connectionsLoaded', handleConnectionsLoaded);
        window.addEventListener('fuzzyConnectionsPreference', handleFuzzyConnectionsPreference);
        window.addEventListener('degreeCheckboxChange', handleDegreeCheckboxChange);
        
        return () => {
            window.removeEventListener('connectionsLoaded', handleConnectionsLoaded);
            window.removeEventListener('fuzzyConnectionsPreference', handleFuzzyConnectionsPreference);
            window.removeEventListener('degreeCheckboxChange', handleDegreeCheckboxChange);
        };
    }, [includeFuzzy, showSecondDegree, showThirdDegree]);

    // Render the graph whenever graphData changes
    useEffect(() => {
        if (graphData.nodes.length > 0) {
            renderD3Graph(graphData);
        }
    }, [graphData]);

    return (
        <div>
            <div className="graph-container" style={{ width: '100%', height: '70vh', textAlign: 'center' }}>
                {graphData.nodes.length > 0 ? (
                    <svg ref={svgRef} style={{ width: '100%', height: '100%' }}></svg>
                ) : (
                    <div style={{ paddingTop: '100px' }}>
                        <p>No graph data available. Search for papers and select connection levels to view the graph.</p>
                    </div>
                )}
            </div>
            
            {selectedPaper && (
                <div className="paper-info-pane">
                    <h3>{selectedPaper.name}</h3>
                    <div className="paper-info-content">
                        <p><strong>ID:</strong> {selectedPaper.id}</p>
                        {selectedPaper.authors && (
                            <p><strong>Authors:</strong> {selectedPaper.authors}</p>
                        )}
                        {selectedPaper.year && (
                            <p><strong>Year:</strong> {selectedPaper.year}</p>
                        )}
                        {selectedPaper.categories && (
                            <p><strong>Categories:</strong> {selectedPaper.categories}</p>
                        )}
                        <p><strong>Connection Level:</strong> {
                            selectedPaper.level === 0 ? "Source paper" : 
                            selectedPaper.level === 1 ? "First degree" : 
                            selectedPaper.level === 2 ? "Second degree" : 
                            "Third degree"
                        }</p>
                        <p><strong>Connection Type:</strong> {
                            selectedPaper.isFuzzy ? "Embedding-based" : "Citation-based"
                        }</p>
                        <div className="abstract-container">
                            <strong>Abstract:</strong>
                            <p className="paper-abstract">
                                {selectedPaper.isLoading ? (
                                    <span className="loading-text">Loading abstract...</span>
                                ) : (
                                    selectedPaper.abstract
                                )}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Graph;