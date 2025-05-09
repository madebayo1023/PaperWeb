import React, { useState } from 'react';

function TopicSearch({ onSearchResults = () => {} }) {
    const [topicQuery, setTopicQuery] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchResults, setSearchResults] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);

    const handleInputChange = (e) => {
        setTopicQuery(e.target.value);
    };

    const notifyConnectionsLoaded = (data) => {
        console.log("DEBUG: Notifying graph with connection data structure:", Object.keys(data));
        const event = new CustomEvent('connectionsLoaded', { detail: data });
        window.dispatchEvent(event);
    };

    const handleSearch = async () => {
        if (!topicQuery.trim()) {
            setError("Please enter a topic to search");
            return;
        }
        
        console.log(`DEBUG: Topic search for: "${topicQuery}"`);
        setIsLoading(true);
        setError(null);
        
        try {
            const url = `http://localhost:8080/api/topic-search?q=${encodeURIComponent(topicQuery)}`;
            console.log(`DEBUG: Requesting topic embeddings for dropdown: ${url}`);
            
            const response = await fetch(url);
            console.log(`DEBUG: Response status: ${response.status}`);
            
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            const text = await response.text();
            console.log(`DEBUG: Response size: ${text.length} bytes`);
            
            const data = JSON.parse(text);
            
            if (!data.success) {
                throw new Error(data.error || "Unknown error");
            }
    
            if (!data.results || data.results.length === 0) {
                console.log("DEBUG: No results found");
                setError("No results found");
                onSearchResults([]);
                setSearchResults([]);
                setShowDropdown(false);
                return;
            }
            
            console.log(`DEBUG: Found ${data.results.length} papers for dropdown`);
            // Store the lightweight results for the dropdown
            setSearchResults(data.results);
            setShowDropdown(true);
            
        } catch (err) {
            console.log(`DEBUG: Topic search error: ${err.message}`);
            setError(err.message || "Search failed");
            setSearchResults([]);
            setShowDropdown(false);
        } finally {
            setIsLoading(false);
        }
    };

    const selectPaper = async (paper) => {
        console.log(`DEBUG: Selected paper: ${paper.id} - ${paper.title}`);
        setIsLoading(true);
        setShowDropdown(false);
        
        try {
            // Now run a full search for just this one paper
            const searchUrl = `http://localhost:8080/api/search?q=${encodeURIComponent(paper.id)}`;
            console.log(`DEBUG: Running FULL search for selected paper: ${searchUrl}`);
            
            const response = await fetch(searchUrl);
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.success || !data.results || data.results.length === 0) {
                throw new Error("Failed to get paper details");
            }
            
            // Use the detailed paper information
            const detailedPaper = data.results[0];
            console.log(`DEBUG: Got detailed info for paper: ${detailedPaper.id}`);
            
            // Update UI with the detailed paper
            onSearchResults([detailedPaper]);
            
            // Update paper title display
            document.getElementById('paperTitle').textContent = detailedPaper.title;
            document.getElementById('paperTitle').hidden = false;
            
            // Notify graph component with connections data
            if (detailedPaper.connections) {
                console.log(`DEBUG: Notifying graph with connection data`);
                notifyConnectionsLoaded(detailedPaper.connections);
            }
        } catch (err) {
            console.log(`DEBUG: Error getting paper details: ${err.message}`);
            setError(`Error loading paper: ${err.message}`);
            setShowDropdown(true); // Reshow dropdown if there's an error
        } finally {
            setIsLoading(false);
        }
    };

    // Handle Enter key press
    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    };

    return (
        <div className="search-container">
            <h3>Search by Topic</h3>
            <input
                type="text"
                className='topicSearchText'
                value={topicQuery}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder="Enter a research topic or try 'machine learning', 'neural networks', 'transformers'"
                style={{ width: '100%' }}
            />
            <button 
                className='search-button' 
                onClick={handleSearch} 
                disabled={isLoading}
                style={{ marginTop: '10px', float: 'right' }}
            >
                {isLoading ? 'Searching...' : 'Search Topic'}
            </button>
            {error && <div style={{ color: 'red', clear: 'both', paddingTop: '10px' }}>{error}</div>}
            
            {showDropdown && searchResults.length > 0 && (
                <div 
                    className="search-results-dropdown"
                    style={{ 
                        marginTop: '10px', 
                        clear: 'both', 
                        maxHeight: '300px', 
                        overflowY: 'auto',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        padding: '10px'
                    }}
                >
                    <h4>Most Relevant Papers:</h4>
                    <div style={{ fontSize: '0.8em', color: '#666', marginBottom: '10px' }}>
                        Click a paper to run a full search
                    </div>
                    <ul style={{ listStyleType: 'none', padding: 0 }}>
                        {searchResults.map((paper, index) => (
                            <li 
                                key={paper.id} 
                                onClick={() => selectPaper(paper)}
                                style={{ 
                                    padding: '8px', 
                                    cursor: 'pointer',
                                    borderBottom: index < searchResults.length - 1 ? '1px solid #eee' : 'none',
                                    backgroundColor: 'white',
                                    hover: { backgroundColor: '#f5f5f5' }
                                }}
                                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                                onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'white'}
                            >
                                <div><strong>{paper.title}</strong></div>
                                <div style={{ fontSize: '0.8em', color: '#666' }}>
                                    {paper.authors} ({paper.year || 'N/A'})
                                </div>
                                <div style={{ fontSize: '0.7em', color: '#999' }}>
                                    Similarity: {(paper.similarity * 100).toFixed(1)}%
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}

export default TopicSearch; 