import React from 'react';

function SideBar() {
    return (
        <div className="sidebar-container">
            <div className='side-papers'>
                <h1 style={{textAlign: 'center'}}>Core Papers</h1>
                <div className='paper-display' id='corePapersDisplay' hidden={true}>
                    <h3 id="corePaper1">1. Paper 1</h3>
                    <h3 id="corePaper2">2. Paper 2</h3>
                    <h3 id="corePaper3">3. Paper 3</h3>
                    <h3 id="corePaper4">4. Paper 4</h3>
                    <h3 id="corePaper5">5. Paper 5</h3>
                </div>
            </div>
            <div className='side-papers'>
                <h1 style={{textAlign: 'center'}}>Hot Papers</h1>
                <div className='paper-display' id='hotPapersDisplay' hidden={true}>
                    <h3 id="hotPaper1">1. Paper 1</h3>
                    <h3 id="hotPaper2">2. Paper 2</h3>
                    <h3 id="hotPaper3">3. Paper 3</h3>
                    <h3 id="hotPaper4">4. Paper 4</h3>
                    <h3 id="hotPaper5">5. Paper 5</h3>
                </div>
            </div>
        </div>
    );
}

export default SideBar;