import React, { useState, useEffect } from 'react';

function CheckboxWithLabel({ label, ...props }) {
    return (
      <div className="checkbox-container">
        <label htmlFor={props.id}>{label}</label>
        <input type="checkbox" id={props.id} {...props} />
      </div>
    );
  }

function DegreeCheckbox({ onConnectionsLoaded = () => {} }) {
  const [secDegChecked, setSecDegChecked] = useState(false);
  const [thirdDegChecked, setThirdDegChecked] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const searchInput = document.querySelector('.searchBarText');
  const paperId = searchInput?.value;

  // Notify the Graph component about checkbox state changes
  const notifyDegreeCheckboxChange = () => {
    const event = new CustomEvent('degreeCheckboxChange', { 
      detail: { 
        showSecondDegree: secDegChecked, 
        showThirdDegree: thirdDegChecked 
      } 
    });
    window.dispatchEvent(event);
  };

  // Notify after component mounts
  useEffect(() => {
    notifyDegreeCheckboxChange();
  }, [secDegChecked, thirdDegChecked]);

  const notifyConnectionsLoaded = (data) => {
    // Create a custom event to notify the Graph component
    const event = new CustomEvent('connectionsLoaded', { detail: data });
    window.dispatchEvent(event);
    
    // Also call the prop function for backward compatibility
    onConnectionsLoaded(data);
  };

  const fetchConnections = async (degreeChecked) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/connections/${encodeURIComponent(paperId)}/${encodeURIComponent(degreeChecked)}`, {
        headers: {
            'Accept': 'application/json'
        }
      });
        
      if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log(data);
      notifyConnectionsLoaded(data);
    } catch (err) {
        setError("Failed to fetch connections");
        console.error("Connection error:", err);
    } finally {
        setIsLoading(false);
    }
  };

  const handleSecCheckboxChange = (event) => {
    const newValue = event.target.checked;
    setSecDegChecked(newValue);
    
    if (newValue && paperId) {
      console.log("showing 1st, 2nd degree connections for", paperId);
      fetchConnections(2)
    }
    // unchecking 2nd degree will automatically also unselect 3rd degree if it is checked
    else if (paperId) {
      setThirdDegChecked(false);
      fetchConnections(1)
      console.log("showing 1st degree connections for", paperId);
    }
  };

  const handleThirdCheckboxChange = (event) => {
    const newValue = event.target.checked;
    setThirdDegChecked(newValue);
    
    // choosing 3rd degree connections w/o 2nd degree will automatically also select 2nd degree
    if (newValue) {
      setSecDegChecked(true);
    }
    
    if (newValue && paperId) {
      console.log("showing 1st, 2nd, and 3rd degree connections for", paperId);
      fetchConnections(3);
    }
    else if (paperId) {
      console.log("showing 1st, 2nd degree connections for", paperId);
      fetchConnections(2);
    }
  };

  return (
    <div className="degree-checkbox-container">
        <CheckboxWithLabel className='checkbox' id="secDegree" label="2nd degree connections" checked={secDegChecked} onChange={handleSecCheckboxChange} disabled={isLoading} />
        <CheckboxWithLabel className='checkbox' id="thirdDegree" label="3rd degree connections" checked={thirdDegChecked} onChange={handleThirdCheckboxChange} disabled={isLoading}/>
        {isLoading && <div>Loading connections...</div>}
        {error && <div style={{ color: 'red' }}>{error}</div>}
    </div>
  );
}

export default DegreeCheckbox;