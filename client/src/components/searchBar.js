import React, { useState } from 'react';
// /Users/mutma_a/CS 510/PaperWeb/client/src/components/searchBar.js
function SearchBar({ onSearchResults = () => {} }) {
    const [query, setQuery] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleInputChange = (e) => {
        setQuery(e.target.value);
    };

    const notifyConnectionsLoaded = (data) => {
        console.log("DEBUG: Notifying graph with connection data structure:", Object.keys(data));
        const event = new CustomEvent('connectionsLoaded', { detail: data });
        window.dispatchEvent(event);
    };

    // Format ArXiv ID if it looks like one (e.g., "2502.08820" or just numbers)
    const formatArxivId = (input) => {
        // If it's already in the format XXXX.XXXXX, return as is
        if (/^\d{4}\.\d{4,5}$/.test(input.trim())) {
            return input.trim();
        }
        
        // If it's just numbers without dots, try to format it as ArXiv ID
        if (/^\d+$/.test(input.trim()) && input.trim().length >= 8) {
            const id = input.trim();
            if (id.length >= 8) {
                return `${id.substring(0, 4)}.${id.substring(4)}`;
            }
        }
        
        return input; // Return original if not recognized as ArXiv ID
    };

    const handleSearch = async () => {
        if (!query.trim()) {
            setError("Please enter a search term");
            return;
        }
        
        // Try to format as ArXiv ID if applicable
        const formattedQuery = formatArxivId(query);
        console.log(`DEBUG: Regular search for: ${formattedQuery}`);
        
        setIsLoading(true);
        setError(null);
        
        try {
            const url = `http://localhost:8080/api/search?q=${encodeURIComponent(formattedQuery)}`;
            console.log(`DEBUG: Requesting: ${url}`);
            
            const response = await fetch(url);
            console.log(`DEBUG: Response status: ${response.status}`);
            
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            const data = JSON.parse(await response.text());
            
            if (!data.success) {
                throw new Error(data.error || "Unknown error");
            }
    
            if (!data.results || data.results.length === 0) {
                // If no results found with formatted query, try direct ID query
                if (formattedQuery !== query && /\d/.test(query)) {
                    try {
                        const directUrl = `http://localhost:8080/api/connections/${encodeURIComponent(query)}/1`;
                        console.log(`DEBUG: Trying direct ID lookup: ${directUrl}`);
                        
                        const directResponse = await fetch(directUrl);
                        console.log(`DEBUG: Direct lookup status: ${directResponse.status}`);
                        
                        if (directResponse.ok) {
                            const connectionData = await directResponse.json();
                            console.log(`DEBUG: Direct connection data:`, connectionData);
                            
                            // If we get a valid connection, display it
                            if (connectionData && connectionData.first_degree) {
                                const sourceId = connectionData.first_degree.source_id;
                                const sourceTitle = connectionData.first_degree.source_title || "Paper " + sourceId;
                                
                                // Create a minimal result object
                                const minimalResult = [{
                                    id: sourceId,
                                    title: sourceTitle,
                                    connections: connectionData
                                }];
                                
                                console.log(`DEBUG: Found paper by direct ID: ${sourceId}`);
                                onSearchResults(minimalResult);
                                document.getElementById('paperTitle').textContent = sourceTitle;
                                document.getElementById('paperTitle').hidden = false;
                                
                                // Notify graph component
                                notifyConnectionsLoaded(connectionData);
                                return;
                            }
                        }
                    } catch (directErr) {
                        // Fallback to showing no results
                    }
                }
                
                // If all attempts failed
                console.log(`DEBUG: No results found for query`);
                setError("No results found. Try a different search term or format.");
                onSearchResults([]);
                return;
            }
            
            console.log(`DEBUG: Found ${data.results.length} results`);
            onSearchResults(data.results);
            let paperTitle = data.results[0].title;
            
            // display paper title on frontend
            document.getElementById('paperTitle').textContent = paperTitle;
            document.getElementById('paperTitle').hidden = false;
            
            // display core paper titles if they exist
            if (data.results[0].hot_papers && data.results[0].hot_papers.length > 0) {
                console.log(`DEBUG: Displaying ${data.results[0].hot_papers.length} hot papers`);
                
                // Also display the same papers in the Hot Papers section
                for (let i = 0; i < Math.min(5, data.results[0].hot_papers.length); i++) {
                    const element = document.getElementById(`hotPaper${i + 1}`);
                    if (element) {
                        element.textContent = `${i + 1}. ${data.results[0].hot_papers[i].title}`;
                    }
                }
                const hotDisplay = document.getElementById('hotPapersDisplay');
                if (hotDisplay) {
                    hotDisplay.hidden = false;
                }
            }

            if (data.results[0].core_papers && data.results[0].core_papers.length > 0) {
                console.log(`DEBUG: Displaying ${data.results[0].core_papers.length} core papers`);
                for (let i = 0; i < Math.min(5, data.results[0].core_papers.length); i++) {
                    const element = document.getElementById(`corePaper${i + 1}`);
                    if (element) {
                        element.textContent = `${i + 1}. ${data.results[0].core_papers[i].title}`;
                    }
                }
                const coreDisplay = document.getElementById('corePapersDisplay');
                if (coreDisplay) {
                    coreDisplay.hidden = false;
                }
            }

            
            // Notify graph component with connections data
            if (data.results[0] && data.results[0].connections) {
                console.log(`DEBUG: Notifying graph with connection data`);
                notifyConnectionsLoaded(data.results[0].connections);
            }
            
        } catch (err) {
            console.log(`DEBUG: Search error: ${err.message}`);
            setError(err.message || "Search failed");
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
            <input
                type="text"
                className='searchBarText'
                value={query}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder="Enter an ArXiv paper title, DOI, ArXiv ID (e.g. 2502.08820), or Category"
                style={{ width: '100%', marginTop: '40px' }}
            />
            <button 
                className='search-button' 
                onClick={handleSearch} 
                disabled={isLoading}
                style={{ marginTop: '10px', float: 'right' }}
            >
                {isLoading ? 'Searching...' : 'Enter'}
            </button>
            {error && <div style={{ color: 'red', clear: 'both', paddingTop: '10px' }}>{error}</div>}
        </div>
    );
}

export default SearchBar;