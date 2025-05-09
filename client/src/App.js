import './App.css';
import React from 'react';
import SearchBar from "../src/components/searchBar.js";
import TopicSearch from "../src/components/topicSearch.js";
import DegreeCheckbox from "../src/components/degreeCheckbox.js";
import FuzzyConnectionsCheckbox from "../src/components/fuzzyConnectionsCheckbox.js";
import Graph from "../src/components/graph.js";
import SideBar from "../src/components/sideBar.js";

function App() {
  React.useEffect(() => {    
    setTimeout(() => {
      const pageContainer = document.querySelector('.page-container');
      const mainContent = document.querySelector('.main-content');
      const sideBar = document.querySelector('.side-bar-div');
    }, 1000);
  }, []);

  return (
    <div className="app-container">
      <header>
        <h1 className="app-title">PaperWeb</h1>
      </header>
      
      <div className="search-section">
        <div className="search-controls">
          <div className="search-inputs">
            <SearchBar />
            <TopicSearch />
          </div>
          <div className="checkbox-controls">
            <DegreeCheckbox />
            <FuzzyConnectionsCheckbox />
          </div>
          <h2 id='paperTitle' hidden={true} className="paper-main-title">Paper Title</h2>
        </div>
      </div>
      
      <div className="page-container">
        <div className="main-content">
          <Graph />
        </div>
        <div className="side-bar-div">
          <SideBar />
        </div>
      </div>
    </div>
  );
}

export default App;