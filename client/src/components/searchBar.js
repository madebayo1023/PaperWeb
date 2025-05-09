import React, { useState } from 'react';
// /Users/mutma_a/CS 510/PaperWeb/client/src/components/searchBar.js
function SearchBar({ onSearchResults = () => {} }) {
    const [query, setQuery] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [categoryResults, setCategoryResults] = useState([]);
    const [showCategoryDropdown, setShowCategoryDropdown] = useState(false);

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

    // Check if input looks like a category (CS.XX or similar)
    const isCategoryQuery = (input) => {
        // Match CS.XX, cs.xx, CS.XXX, etc.
        return /^(?:cs\.|CS\.)?\w{2,5}$/i.test(input.trim());
    };

    const handleSearch = async () => {
        if (!query.trim()) {
            setError("Please enter a search term");
            return;
        }
        
        setIsLoading(true);
        setError(null);
        setCategoryResults([]);
        setShowCategoryDropdown(false);
        
        // Check if this is a category search
        if (isCategoryQuery(query)) {
            try {
                console.log(`DEBUG: Trying category search for: ${query}`);
                const categoryUrl = `http://localhost:8080/api/category-search?category=${encodeURIComponent(query)}`;
                const response = await fetch(categoryUrl);
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.results && data.results.length > 0) {
                        console.log(`DEBUG: Found ${data.results.length} papers for category ${data.category}`);
                        setCategoryResults(data.results);
                        setShowCategoryDropdown(true);
                        setIsLoading(false);
                        return;
                    }
                }
                // If category search fails, continue with regular search
                console.log("DEBUG: Category search found no results, trying regular search");
            } catch (categoryErr) {
                console.log(`DEBUG: Category search error: ${categoryErr.message}`);
                // Continue with regular search if category search fails
            }
        }
        
        // Try to format as ArXiv ID if applicable
        const formattedQuery = formatArxivId(query);
        console.log(`DEBUG: Regular search for: ${formattedQuery}`);
        
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
                
                // Clear previous hot papers first
                for (let i = 1; i <= 5; i++) {
                    const element = document.getElementById(`hotPaper${i}`);
                    if (element) {
                        element.textContent = `${i}. `;
                    }
                }
                
                // Display hot papers
                for (let i = 0; i < Math.min(5, data.results[0].hot_papers.length); i++) {
                    const hotPaper = data.results[0].hot_papers[i];
                    if (hotPaper && hotPaper.title) {
                        const element = document.getElementById(`hotPaper${i + 1}`);
                        if (element) {
                            element.textContent = `${i + 1}. ${hotPaper.title}`;
                        }
                    }
                }
                
                const hotDisplay = document.getElementById('hotPapersDisplay');
                if (hotDisplay) {
                    hotDisplay.hidden = data.results[0].hot_papers.length === 0;
                }
            } else {
                // Hide hot papers section if no results
                const hotDisplay = document.getElementById('hotPapersDisplay');
                if (hotDisplay) {
                    hotDisplay.hidden = true;
                }
            }

            if (data.results[0].core_papers && data.results[0].core_papers.length > 0) {
                console.log(`DEBUG: Displaying ${data.results[0].core_papers.length} core papers`);
                
                // Clear previous core papers first
                for (let i = 1; i <= 5; i++) {
                    const element = document.getElementById(`corePaper${i}`);
                    if (element) {
                        element.textContent = `${i}. `;
                    }
                }
                
                // Display core papers
                for (let i = 0; i < Math.min(5, data.results[0].core_papers.length); i++) {
                    const corePaper = data.results[0].core_papers[i];
                    if (corePaper && corePaper.title) {
                        const element = document.getElementById(`corePaper${i + 1}`);
                        if (element) {
                            element.textContent = `${i + 1}. ${corePaper.title}`;
                        }
                    }
                }
                
                const coreDisplay = document.getElementById('corePapersDisplay');
                if (coreDisplay) {
                    coreDisplay.hidden = data.results[0].core_papers.length === 0;
                }
            } else {
                // Hide core papers section if no results
                const coreDisplay = document.getElementById('corePapersDisplay');
                if (coreDisplay) {
                    coreDisplay.hidden = true;
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

    // Handle selection of a paper from the category dropdown
    const selectCategoryPaper = async (paper) => {
        console.log(`DEBUG: Selected paper from category: ${paper.id} - ${paper.title}`);
        setIsLoading(true);
        setShowCategoryDropdown(false);
        
        try {
            // Run a regular search for this paper
            const searchUrl = `http://localhost:8080/api/search?q=${encodeURIComponent(paper.id)}`;
            console.log(`DEBUG: Running search for selected paper by ID: ${searchUrl}`);
            
            const response = await fetch(searchUrl);
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.success || !data.results || data.results.length === 0) {
                // If search fails, use the basic paper information we already have
                console.log(`DEBUG: Detailed search failed, using basic paper info`);
                
                // Create a minimal result object
                const minimalResult = [{
                    id: paper.id,
                    title: paper.title,
                    authors: paper.authors,
                    categories: paper.categories,
                    year: paper.year
                }];
                
                onSearchResults(minimalResult);
                document.getElementById('paperTitle').textContent = paper.title;
                document.getElementById('paperTitle').hidden = false;
                
                // Show message about limited information
                setError("Only basic paper information is available.");
                return;
            }
            
            // Use the detailed paper information
            console.log(`DEBUG: Got detailed info for paper: ${data.results[0].id}`);
            onSearchResults(data.results);
            
            // Update paper title display
            document.getElementById('paperTitle').textContent = data.results[0].title;
            document.getElementById('paperTitle').hidden = false;
            
            // Display other sections if available
            if (data.results[0].hot_papers && data.results[0].hot_papers.length > 0) {
                console.log(`DEBUG: Displaying ${data.results[0].hot_papers.length} hot papers`);
                
                // Clear previous hot papers first
                for (let i = 1; i <= 5; i++) {
                    const element = document.getElementById(`hotPaper${i}`);
                    if (element) {
                        element.textContent = `${i}. `;
                    }
                }
                
                // Display hot papers
                for (let i = 0; i < Math.min(5, data.results[0].hot_papers.length); i++) {
                    const hotPaper = data.results[0].hot_papers[i];
                    if (hotPaper && hotPaper.title) {
                        const element = document.getElementById(`hotPaper${i + 1}`);
                        if (element) {
                            element.textContent = `${i + 1}. ${hotPaper.title}`;
                        }
                    }
                }
                
                const hotDisplay = document.getElementById('hotPapersDisplay');
                if (hotDisplay) {
                    hotDisplay.hidden = data.results[0].hot_papers.length === 0;
                }
            } else {
                // Hide hot papers section if no results
                const hotDisplay = document.getElementById('hotPapersDisplay');
                if (hotDisplay) {
                    hotDisplay.hidden = true;
                }
            }
            
            if (data.results[0].core_papers && data.results[0].core_papers.length > 0) {
                console.log(`DEBUG: Displaying ${data.results[0].core_papers.length} core papers`);
                
                // Clear previous core papers first
                for (let i = 1; i <= 5; i++) {
                    const element = document.getElementById(`corePaper${i}`);
                    if (element) {
                        element.textContent = `${i}. `;
                    }
                }
                
                // Display core papers
                for (let i = 0; i < Math.min(5, data.results[0].core_papers.length); i++) {
                    const corePaper = data.results[0].core_papers[i];
                    if (corePaper && corePaper.title) {
                        const element = document.getElementById(`corePaper${i + 1}`);
                        if (element) {
                            element.textContent = `${i + 1}. ${corePaper.title}`;
                        }
                    }
                }
                
                const coreDisplay = document.getElementById('corePapersDisplay');
                if (coreDisplay) {
                    coreDisplay.hidden = data.results[0].core_papers.length === 0;
                }
            } else {
                // Hide core papers section if no results
                const coreDisplay = document.getElementById('corePapersDisplay');
                if (coreDisplay) {
                    coreDisplay.hidden = true;
                }
            }
            
            // Notify graph component with connections data
            if (data.results[0] && data.results[0].connections) {
                notifyConnectionsLoaded(data.results[0].connections);
            }
        } catch (err) {
            console.log(`DEBUG: Error getting paper details: ${err.message}`);
            setError(`Error loading paper: ${err.message}`);
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
                placeholder="Enter an ArXiv ID (e.g. 2502.08820) or Category (e.g. CS.CL)"
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
            
            {showCategoryDropdown && categoryResults.length > 0 && (
                <div 
                    className="category-results-dropdown"
                    style={{ 
                        marginTop: '50px', 
                        clear: 'both', 
                        maxHeight: '400px', 
                        overflowY: 'auto',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        padding: '10px',
                        backgroundColor: '#f9f9f9'
                    }}
                >
                    <h4>Recent Papers in Category {query.toUpperCase().startsWith("CS.") ? query.toUpperCase() : `CS.${query.toUpperCase()}`}</h4>
                    <div style={{ fontSize: '0.8em', color: '#666', marginBottom: '10px' }}>
                        Click a paper to view details
                    </div>
                    <ul style={{ listStyleType: 'none', padding: 0 }}>
                        {categoryResults.map((paper, index) => (
                            <li 
                                key={paper.id} 
                                onClick={() => selectCategoryPaper(paper)}
                                style={{ 
                                    padding: '10px', 
                                    cursor: 'pointer',
                                    borderBottom: index < categoryResults.length - 1 ? '1px solid #eee' : 'none',
                                    backgroundColor: 'white',
                                    marginBottom: '5px',
                                    borderRadius: '4px'
                                }}
                                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f0f0f0'}
                                onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'white'}
                            >
                                <div style={{ fontWeight: 'bold' }}>{paper.title}</div>
                                <div style={{ fontSize: '0.8em', color: '#666' }}>
                                    {paper.authors} ({paper.year || 'N/A'})
                                </div>
                                <div style={{ fontSize: '0.7em', color: '#999' }}>
                                    {paper.id}
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}

export default SearchBar;