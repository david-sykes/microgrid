// Initialize the visualization
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM content loaded');
    
    // Initialize with empty network data
    let networkData = null;
    
    // Load network data from data.json
    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            networkData = data;
            console.log('Network data loaded successfully');
            // Draw the network with the loaded data
            drawNetwork(networkData, 0);
        })
        .catch(error => {
            console.error('Error loading network data:', error);
            // Draw sample network if data loading fails
            drawNetwork(null, 0);
        });
    
    // DOM elements
    const selectElementBtn = document.getElementById('select-element-btn');
    const graphPopup = document.getElementById('graph-popup');
    const closeGraphBtn = document.getElementById('close-graph-btn');
    const timestepSlider = document.getElementById('timestep-slider');
    
    // Event listeners
    selectElementBtn.addEventListener('click', () => {
        // Simulate selecting a network element
        showGraphPopup();
    });
    
    closeGraphBtn.addEventListener('click', () => {
        hideGraphPopup();
    });
    
    timestepSlider.addEventListener('input', (e) => {
        const timestep = e.target.value;
        console.log(`Timestep changed to: ${timestep}`);
        // Update visualization based on timestep
        updateVisualization(timestep);
    });
    
    // Functions
    function showGraphPopup() {
        graphPopup.classList.remove('hidden');
    }
    
    function hideGraphPopup() {
        graphPopup.classList.add('hidden');
    }
    
    function updateVisualization(timestep) {
        // This function will update the network visualization based on the timestep
        console.log(`Updating visualization for timestep ${timestep}`);
        drawNetwork(networkData, timestep);
    }

    // Keep track of the network instance
    let networkInstance = null;
    
    function drawNetwork(networkData, timestep) {
        console.log('Drawing network with data:', networkData);
        
        // Create a network
        var container = document.getElementById('network-visualization');
        
        // Find or create the network div
        let networkDiv = document.getElementById('network-vis-container');
        if (!networkDiv) {
            // Create a new div for the network
            networkDiv = document.createElement('div');
            networkDiv.id = 'network-vis-container';
            networkDiv.style.width = '100%';
            networkDiv.style.height = '100%';
            networkDiv.style.position = 'absolute';
            networkDiv.style.top = '0';
            networkDiv.style.left = '0';
            networkDiv.style.zIndex = '1';
            container.appendChild(networkDiv);
        }
        
        // If we already have a network instance, destroy it to prevent memory leaks
        if (networkInstance) {
            networkInstance.destroy();
            networkInstance = null;
        }
        
        // Draw buses
        var nodes = [];

        for (let bus in networkData.network.buses) {
            nodes.push({
                id: bus,
                label: bus || `Bus ${bus}`,
                shape: 'box'
            });
          }

        
        // Create edges
        var edges = [];\

        for (let line in networkData.network.transmission_lines){
            edges.push({
                from: line.from_bus,
                to: line.to_bus,
                color: { color: 'blue' }
            });
        }
       
    
        // Ensure controls are above the network
        const timestepControl = document.querySelector('.timestep-control');
        if (timestepControl) {
            timestepControl.style.zIndex = '10';
        }
        if (selectElementBtn) {
            selectElementBtn.style.zIndex = '10';
        }
        
        // Create vis.js datasets
        var visNodes = new vis.DataSet(nodes);
        var visEdges = new vis.DataSet(edges);
        
        var data = {
            nodes: visNodes,
            edges: visEdges
        };
        
        var options = {
            nodes: {
                shape: 'circle',
                font: {
                    size: 14
                }
            },
            edges: {
                width: 2
            }
        };
        
        // Create the network
        try {
            networkInstance = new vis.Network(networkDiv, data, options);
            
            // Add event listener for node selection
            networkInstance.on('selectNode', function(params) {
                console.log('Node selected:', params.nodes[0]);
                showGraphPopup();
            });
        } catch (e) {
            console.error('Error creating network:', e);
        }
    }
    
    // Initialize with graph popup hidden
    hideGraphPopup();
});
