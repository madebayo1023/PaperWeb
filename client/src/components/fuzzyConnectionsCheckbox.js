import React, { useState, useEffect } from 'react';

function CheckboxWithLabel({ label, ...props }) {
  return (
    <div className="checkbox-container">
      <label htmlFor={props.id}>{label}</label>
      <input type="checkbox" id={props.id} {...props} />
    </div>
  );
}

function FuzzyConnectionsCheckbox() {
  const [includeFuzzy, setIncludeFuzzy] = useState(true);
  
  // This function will notify the Graph component about the fuzzy connections preference
  const notifyFuzzyConnectionsPreference = (includeFuzzy) => {
    const event = new CustomEvent('fuzzyConnectionsPreference', { 
      detail: { includeFuzzy } 
    });
    window.dispatchEvent(event);
  };

  // Handle checkbox change
  const handleCheckboxChange = (event) => {
    const newValue = event.target.checked;
    setIncludeFuzzy(newValue);
    notifyFuzzyConnectionsPreference(newValue);
  };

  // Initialize on first render
  useEffect(() => {
    notifyFuzzyConnectionsPreference(includeFuzzy);
  }, []);

  return (
    <div className="fuzzy-checkbox-container">
      <CheckboxWithLabel 
        className='checkbox' 
        id="includeFuzzy" 
        label="Include embedding-based connections" 
        checked={includeFuzzy} 
        onChange={handleCheckboxChange} 
      />
    </div>
  );
}

export default FuzzyConnectionsCheckbox; 