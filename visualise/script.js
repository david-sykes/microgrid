// Initialize the visualization
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM content loaded');
    
    // Initialize with empty network data
    let networkData = null;
    let visNodes = null;
    let visEdges = null;
    let generatorChart; // global ref so we can destroy/update later
    let busChart; // global ref so we can destroy/update later
    let storageChart; // global ref so we can destroy/update later
    let loadChart; // global ref so we can destroy/update later

    // Load network data from data.json
    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            networkData = data;
            console.log('Network data loaded successfully');
            
            // Set up the timestep slider based on the data
            setupTimestepSlider(networkData);
            
            // Draw the network with the loaded data
            drawNetwork(networkData, 0);
        })
        .catch(error => {
            console.error('Error loading network data:', error);
            // Draw sample network if data loading fails
            drawNetwork(null, 0);
        });
    
    // DOM elements
    const graphPopup = document.getElementById('graph-popup');
    const closeGraphBtn = document.getElementById('close-graph-btn');
    const timestepSlider = document.getElementById('timestep-slider');
    
    // Event listeners
    closeGraphBtn.addEventListener('click', () => {
        hideGraphPopup();
    });
    
    timestepSlider.addEventListener('input', (e) => {
        const timestepIndex = parseInt(e.target.value, 10);
        console.log(`Timestep changed to index: ${timestepIndex}`);
        // Update visualization based on timestep
        updateVisualization(timestepIndex);
    });
    
    // Set up the timestep slider based on the data
    function setupTimestepSlider(data) {
        if (!data || !data.network || !data.network.timesteps) return;
        
        const timesteps = data.network.timesteps;
        const numTimesteps = timesteps.length;
        
        // Set the max value of the slider to the number of timesteps - 1
        timestepSlider.max = numTimesteps - 1;
        timestepSlider.value = 0;
        
        // Add a label to show the current timestep
        const timestepLabel = document.createElement('div');
        timestepLabel.id = 'timestep-label';
        timestepLabel.textContent = `Time: ${timesteps[0][1]}`;
        timestepLabel.style.textAlign = 'center';
        timestepLabel.style.marginTop = '5px';
        
        const timestepControl = document.querySelector('.timestep-control');
        if (timestepControl && !document.getElementById('timestep-label')) {
            timestepControl.appendChild(timestepLabel);
        }
        
        // Update the label when the slider changes
        timestepSlider.addEventListener('input', (e) => {
            const index = parseInt(e.target.value, 10);
            if (timestepLabel && timesteps[index]) {
                timestepLabel.textContent = `Time: ${timesteps[index][1]}`;
            }
        });
    }
    
    // Functions
    function showGraphPopup(nodeId) {
       const node = visNodes.get(nodeId);

       if (node.type === 'bus') {
           renderBusChart(nodeId);
       } else if (node.type === 'generator') {
           renderGeneratorChart(nodeId);
       } else if (node.type === 'load') {
           renderLoadChart(nodeId);
       } else if (node.type === 'storage') {
           renderStorageChart(nodeId);
       }

        // Update the graph popup with data for the selected node
        
        // Show the popup
        graphPopup.classList.remove('hidden');
    }
    
    function hideGraphPopup() {
        graphPopup.classList.add('hidden');
    }
    
    // Keep track of the network instance
    let networkInstance = null;
    
    function drawNetwork(networkData, timestepIndex) {
        // This will be called just once when the page loads

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
        
        // Create nodes
        var nodes = [];
        
        // Create edges
        var edges = [];

        // Add bus nodes
        for (let bus in networkData.network.buses) {
            const busData = networkData.network.buses[bus];
            const nodalPrice = busData.nodal_prices && busData.nodal_prices[timestepIndex] !== undefined 
                ? busData.nodal_prices[timestepIndex].toFixed(2) 
                : 'N/A';
            

                nodes.push({
                    id: bus,
                    label: `${bus}\nNodal Price: ${nodalPrice}`,
                    shape: 'circle',
                    color: {
                        background: '#D2E5FF',
                        border: '#2B7CE9'
                    },
                    type: 'bus'
                });
            
        }

        // Add generator nodes
        for (let bus in networkData.network.buses) {
            for (let generator in networkData.network.buses[bus].generators) {
                const generatorData = networkData.network.buses[bus].generators[generator];
                const output = generatorData.outputs && generatorData.outputs[timestepIndex] !== undefined 
                    ? generatorData.outputs[timestepIndex].toFixed(2) 
                    : 'N/A';
                const capacity = generatorData.capacities && generatorData.capacities[timestepIndex] !== undefined
                    ? generatorData.capacities[timestepIndex].toFixed(2) 
                    : 'N/A';
                nodes.push({
                    id: generator,
                    label: `${generator}\nOutput: ${output} / ${capacity}`,
                    shape: 'box',
                    color: {
                        background: '#FFD700',
                        border: '#FF8C00'
                    },
                    type: 'generator'
                });

                edges.push({
                    id: generator,
                    from: generator,
                    to: bus,
                    color: { color: 'blue' },
                    label: `${output}`
                });
            }
        }

        // Add demand nodes
        for (let bus in networkData.network.buses) {
            for (let load in networkData.network.buses[bus].loads) {
                const loadData = networkData.network.buses[bus].loads[load];
                const consumption = loadData.consumptions && loadData.consumptions[timestepIndex] !== undefined 
                    ? loadData.consumptions[timestepIndex].toFixed(2) 
                    : 'N/A';
                nodes.push({
                    id: load,
                    label: `${load}\nConsumption: ${consumption}`,
                    shape: 'box',
                    color: {
                        background: '#FFD700',
                        border: '#FF8C00'
                    },
                    type: 'load'
                });
                if (consumption > 0){
                edges.push({
                    id: load,
                    from: bus,
                    to: load,
                    color: { color: 'blue' },
                    label: `${consumption}`
                })
            } else if (consumption < 0) {
                edges.push({
                    id: load,
                    from: load,
                    to: bus,
                    color: { color: 'blue' },
                    label: `${-consumption}`
                })

            }
            }
        }

        // Add storage unit nodes
        for (let bus in networkData.network.buses) {
            for (let storage in networkData.network.buses[bus].storage_units) {
                const storageData = networkData.network.buses[bus].storage_units[storage];
                const start_soc = storageData.soc_start_of_ts && storageData.soc_start_of_ts[timestepIndex] !== undefined 
                    ? storageData.soc_start_of_ts[timestepIndex].toFixed(2) 
                    : 'N/A';
                const end_soc = storageData.soc_end_of_ts && storageData.soc_end_of_ts[timestepIndex] !== undefined 
                    ? storageData.soc_end_of_ts[timestepIndex].toFixed(2) 
                    : 'N/A';
                const charge_inflow = storageData.charge_inflows && storageData.charge_inflows[timestepIndex] !== undefined 
                    ? storageData.charge_inflows[timestepIndex].toFixed(2) 
                    : 'N/A';
                const discharge_outflow = storageData.discharge_outflows && storageData.discharge_outflows[timestepIndex] !== undefined 
                    ? storageData.discharge_outflows[timestepIndex].toFixed(2) 
                    : 'N/A';
                const net_inflow = charge_inflow - discharge_outflow;
                const consumption = storageData.consumptions && storageData.consumptions[timestepIndex] !== undefined 
                    ? storageData.consumptions[timestepIndex].toFixed(2)
                    : 'N/A';
                    

                // Add the storage unit
                nodes.push({
                    id: storage,
                    label: `${storage}\nStart SOC: ${start_soc}\nEnd SOC: ${end_soc}`,
                    shape: 'ellipse',
                    color: {
                        background: '#FFD700',
                        border: '#FF8C00'
                    },
                    type: 'storage'
                });

                // Add the storage unit energy sync
                nodes.push({
                    id: `${storage}_consumption`,
                    label: `${storage}\nConsumption: ${consumption}`,
                    shape: 'box',
                    color: {
                        background: '#FFD700',
                        border: '#FF8C00'
                    },
                    type: 'storage_consumption'
                });



                if (net_inflow > 0) {
                    edges.push({
                        id: storage,
                        from: bus,
                        to: storage,
                        color: { color: 'blue' },
                        label: `${net_inflow}`
                    })
                } else {
                    edges.push({
                        id: storage,
                        from: storage,
                        to: bus,
                        color: { color: 'blue' },
                        label: `${-net_inflow}`
                    })
                }

                // Add the storage unit energy sync edge
                edges.push({
                    id: `${storage}_consumption`,
                    from: storage,
                    to: `${storage}_consumption`,
                    color: { color: 'blue' },
                    label: `${consumption}`
                })

            }
        }


        
        // Add transmission lines
        for (let line in networkData.network.transmission_lines) {
            let lineData = networkData.network.transmission_lines[line];
            const flow = lineData.flows && lineData.flows[timestepIndex] !== undefined 
                ? lineData.flows[timestepIndex].toFixed(2) 
                : 'N/A';
            const capacity = lineData.capacities && lineData.capacities[timestepIndex] !== undefined
                ? lineData.capacities[timestepIndex].toFixed(2) 
                : 'N/A';
            if (flow > 0) {
                edges.push({
                    id: line,
                    from: lineData.start_bus,
                    to: lineData.end_bus,
                    color: { color: 'blue' },
                    label: `${flow} / ${capacity}`
                })
            } else {
                edges.push({
                    id: line,
                    from: lineData.end_bus,
                    to: lineData.start_bus,
                    color: { color: 'blue' },
                    label: `${-flow} / ${capacity}`
                })
            }

        }


       
        // Ensure timestep control is above the network
        const timestepControl = document.querySelector('.timestep-control');
        if (timestepControl) {
            timestepControl.style.zIndex = '10';
        }
        
        // Create vis.js datasets
        visNodes = new vis.DataSet(nodes);
        visEdges = new vis.DataSet(edges);
        
        var data = {
            nodes: visNodes,
            edges: visEdges
        };
        
        var options = {
            nodes: {
                shape: 'box',
                font: {
                    size: 14,
                    multi: 'html'
                },
                margin: 10
            },
            edges: {
                width: 2,
                font: {
                    size: 12,
                    align: 'top',
                    multi: 'html'
                },
                arrows: {
                    to: { enabled: true, scaleFactor: 0.5 }
                }
            },
            physics: {
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 200,
                    springConstant: 0.05
                },
                stabilization: {
                    iterations: 100
                }
            },
            interaction: {
                selectConnectedEdges: false,
                multiselect: false
            }
        };
        
        // Create the network
        try {
            networkInstance = new vis.Network(networkDiv, data, options);
            
            // Add event listener for node selection
            networkInstance.on('selectNode', function(params) {
                const nodeId = params.nodes[0];
                console.log('Node selected:', nodeId);
                showGraphPopup(nodeId);
            });
            
        } catch (e) {
            console.error('Error creating network:', e);
        }

        // Disable physics after stabilization
        networkInstance.once("stabilized", () => {
            networkInstance.setOptions({ physics: false });
        });
    }

    function updateVisualization(timestepIndex) {
        // This function will update the network visualization based on the timestep
        console.log(`Updating visualization for timestep index ${timestepIndex}`);
        
        // Update bus nodes
        for (let bus in networkData.network.buses) {
            const busData = networkData.network.buses[bus];
            const nodalPrice = busData.nodal_prices && busData.nodal_prices[timestepIndex] !== undefined 
                ? busData.nodal_prices[timestepIndex].toFixed(2) 
                : 'N/A';
            
            // Update node 
            visNodes.update({
                id: bus,
                label: `${bus}\nNodal Price: ${nodalPrice}`
            });
        }

        // Update generator nodes
        for (let bus in networkData.network.buses) {
            for (let generator in networkData.network.buses[bus].generators) {
                const generatorData = networkData.network.buses[bus].generators[generator];
                const output = generatorData.outputs && generatorData.outputs[timestepIndex] !== undefined 
                    ? generatorData.outputs[timestepIndex].toFixed(2) 
                    : 'N/A';
                const capacity = generatorData.capacities && generatorData.capacities[timestepIndex] !== undefined
                    ? generatorData.capacities[timestepIndex].toFixed(2) 
                    : 'N/A';
                
                // Update node label
                const node = visNodes.get(generator);
                if (node) {
                    node.label = `${generator}\nOutput: ${output} / ${capacity}`;
                    visNodes.update(node);
                }

                // Update edge labels
                const edge = visEdges.get(generator);
                if (edge) {
                    edge.label = `${output}`;
                    visEdges.update(edge);
                }
            }
        }

        // Update load nodes
        for (let bus in networkData.network.buses) {
            for (let load in networkData.network.buses[bus].loads) {
                const loadData = networkData.network.buses[bus].loads[load];
                const consumption = loadData.consumptions && loadData.consumptions[timestepIndex] !== undefined 
                    ? loadData.consumptions[timestepIndex].toFixed(2) 
                    : 'N/A';
                
                // Update node label
                const node = visNodes.get(load);
                if (node) {
                    node.label = `${load}\nConsumption: ${consumption}`;
                    visNodes.update(node);
                }

                // Update edge labels
                const edge = visEdges.get(load);
                if (edge) {
                    if (consumption > 0) {
                    edge.from = bus;
                    edge.to = load;
                    } else if (consumption < 0) {
                    edge.from = load;
                    edge.to = bus;
                    }
                    edge.label = `${consumption}`;
                    visEdges.update(edge);
                }
            }
        }

        // Update storage unit nodes
        for (let bus in networkData.network.buses) {
            for (let storage in networkData.network.buses[bus].storage_units) {
                const storageData = networkData.network.buses[bus].storage_units[storage];
                const start_soc = storageData.soc_start_of_ts && storageData.soc_start_of_ts[timestepIndex] !== undefined 
                    ? storageData.soc_start_of_ts[timestepIndex].toFixed(2) 
                    : 'N/A';
                const end_soc = storageData.soc_end_of_ts && storageData.soc_end_of_ts[timestepIndex] !== undefined 
                    ? storageData.soc_end_of_ts[timestepIndex].toFixed(2) 
                    : 'N/A';
                const charge_inflow = storageData.charge_inflows && storageData.charge_inflows[timestepIndex] !== undefined 
                    ? storageData.charge_inflows[timestepIndex].toFixed(2) 
                    : 'N/A';
                const discharge_outflow = storageData.discharge_outflows && storageData.discharge_outflows[timestepIndex] !== undefined 
                    ? storageData.discharge_outflows[timestepIndex].toFixed(2) 
                    : 'N/A';
                const net_inflow = charge_inflow - discharge_outflow;
                const consumption = storageData.consumptions && storageData.consumptions[timestepIndex] !== undefined 
                    ? storageData.consumptions[timestepIndex].toFixed(2) 
                    : 'N/A';
                
                // Update node label
                const node = visNodes.get(storage);
                if (node) {
                    node.label = `${storage}\nStart SOC: ${start_soc}\nEnd SOC: ${end_soc}`;
                    visNodes.update(node);
                }

                // Update storage consumption node
                const consumptionNode = visNodes.get(`${storage}_consumption`);
                if (consumptionNode) {
                    consumptionNode.label = `${storage}\nConsumption: ${consumption}`;
                    visNodes.update(consumptionNode);
                }

                // Update edge labels
                const edge = visEdges.get(storage);

                if (edge) {
                    if (net_inflow > 0) {
                        edge.from = bus;
                        edge.to = storage;
                        edge.label = `${net_inflow}`;
                        visEdges.update(edge);
                    } else {
                        edge.from = storage;
                        edge.to = bus;
                        edge.label = `${-net_inflow}`;
                        visEdges.update(edge);
                    }
                }

                // Update storage consumption edge
                const consumptionEdge = visEdges.get(`${storage}_consumption`);
                if (consumptionEdge) {
                    consumptionEdge.from = storage;
                    consumptionEdge.to = `${storage}_consumption`;
                    consumptionEdge.label = `${consumption}`;
                    visEdges.update(consumptionEdge);
                }
            }
        }

        // Update transmission line nodes
        for (let line in networkData.network.transmission_lines) {
            const lineData = networkData.network.transmission_lines[line];
            const flow = lineData.flows && lineData.flows[timestepIndex] !== undefined 
                ? lineData.flows[timestepIndex].toFixed(2) 
                : 'N/A';
            const capacity = lineData.capacities && lineData.capacities[timestepIndex] !== undefined
                ? lineData.capacities[timestepIndex].toFixed(2) 
                : 'N/A';
            
            // Update node label
            const edge = visEdges.get(line);
            if (edge) {
                if (flow > 0) {
                    edge.from = lineData.start_bus;
                    edge.to = lineData.end_bus;
                    edge.label = `${flow} / ${capacity}`;
                    visEdges.update(edge);
                } else {
                    edge.from = lineData.end_bus;
                    edge.to = lineData.start_bus;
                    edge.label = `${-flow} / ${capacity}`;
                    visEdges.update(edge);
                }
            }
        }



    }
    
    function generateColor(index, baseHue = 180, saturation = 60, lightness = 60) {
        const hueStep = 30; // tweak to spread hues more or less
        const hue = (baseHue + index * hueStep) % 360;
        return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    }

    function showFlowChart(nodeId) {
        const graphPopup = document.getElementById('graph-popup');
        graphPopup.classList.remove('hidden');
        
        const chartContainer = document.querySelector('.chart-container');
        const canvas = document.getElementById('flow-chart');
        
        // Set canvas size to match container
        canvas.width = chartContainer.offsetWidth;
        canvas.height = chartContainer.offsetHeight;
        
        // Create or update chart
        if (generatorChart) {
            generatorChart.destroy();
        }
        if (busChart) {
            busChart.destroy();
        }
        if (storageChart) {
            storageChart.destroy();
        }
        if (loadChart) {
            loadChart.destroy();
        }

        if (nodeId.type === 'bus') {
            renderBusChart(nodeId);
        } else if (nodeId.type === 'generator') {
            renderGeneratorChart(nodeId);
        } else if (nodeId.type === 'load') {
            renderLoadChart(nodeId);
        } else if (nodeId.type === 'storage') {
            renderStorageChart(nodeId);
        }
    }

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                align: 'start',
                labels: {
                    boxWidth: 15,
                    padding: 15
                }
            }
        },
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Timestep'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Power (MW)'
                }
            }
        }
    };

    function renderBusChart(busId) {

            if (generatorChart) generatorChart.destroy(); // prevent duplicate overlays
            if (busChart) busChart.destroy();
            if (storageChart) storageChart.destroy();
            if (loadChart) loadChart.destroy();

            const ctx = document.getElementById('flow-chart').getContext('2d');
            
            const busData = networkData.network.buses[busId];

            const flows = {
                labels: networkData.network.timesteps,
                datasets: []
            }
            let index = 0;
            // Add generator data if exists
            if (busData.generators) {
                for (let generator in busData.generators) {
                    const generatorData = busData.generators[generator];
                    if (generatorData.outputs) {
                        flows.datasets.push({
                            label: generator,
                            data: generatorData.outputs,
                            backgroundColor: generateColor(index),
                            stack: 'energy'
                        });
                        index++;
                    }
                }
            }

            // Outflows (Loads) as negative
            if (busData.loads) {
                for (let load in busData.loads) {
                    const loadData = busData.loads[load];
                    if (loadData.consumptions) {
                        flows.datasets.push({
                            label: load,
                            data: loadData.consumptions.map(v => -v),
                            backgroundColor: generateColor(index, 300),
                            stack: 'energy'
                        });
                    }
                }
            }

            //  Transmission line flows
            for (let line in networkData.network.transmission_lines) {
                const lineData = networkData.network.transmission_lines[line];
                let color = generateColor(index, 240);
                if (lineData.start_bus === busId) {
                    flows.datasets.push({
                        label: line,
                        data: lineData.flows.map(v => -v),
                        backgroundColor: color,
                        stack: 'energy'
                    })
                        
                } else if (lineData.end_bus === busId){
                    flows.datasets.push({
                        label: line,
                        data: lineData.flows,
                        backgroundColor: color,
                        stack: 'energy'
                    })
                }
            }

            // Storage flows
            for (let storage in busData.storage_units) {
                const storageData = busData.storage_units[storage];
                const charge_inflows = storageData.charge_inflows
                const discharge_outflows = storageData.discharge_outflows
                let color = generateColor(index, 60);
                
                flows.datasets.push({
                    label: storage + " Charge",
                    data: charge_inflows.map(v => -v),
                    backgroundColor: color,
                    stack: 'energy'
                })
                flows.datasets.push({
                    label: storage + " Discharge",
                    data: discharge_outflows,
                    backgroundColor: color,
                    stack: 'energy'
                })
            }

            busChart = new Chart(ctx, {
                type: 'bar',
                data: flows,
                options: chartOptions
            });
        }
    
    function renderGeneratorChart(generatorId){


        if (generatorChart) generatorChart.destroy(); // prevent duplicate overlays
        if (busChart) busChart.destroy();
        if (storageChart) storageChart.destroy();
        if (loadChart) loadChart.destroy();

        const ctx = document.getElementById('flow-chart').getContext('2d');
        for (let bus in networkData.network.buses) {
            const busData = networkData.network.buses[bus];
            if (busData.generators && busData.generators[generatorId]) {
                const generatorData = busData.generators[generatorId];
                const output = generatorData.outputs;
                const outputData = {
                    labels: networkData.network.timesteps,
                    datasets: [{
                        label: generatorId,
                        data: output,
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }]
                };
                generatorChart = new Chart(ctx, {
                    type: 'line',
                    data: outputData,
                    options: chartOptions
                });
                return;
            }
        }

    }
          
    function renderLoadChart(loadId){
        if (generatorChart) generatorChart.destroy(); // prevent duplicate overlays
        if (busChart) busChart.destroy();
        if (storageChart) storageChart.destroy();
        if (loadChart) loadChart.destroy();

        const ctx = document.getElementById('flow-chart').getContext('2d');
        for (let bus in networkData.network.buses) {
            const busData = networkData.network.buses[bus];
            if (busData.loads && busData.loads[loadId]) {
                const loadData = busData.loads[loadId];
                const consumption = loadData.consumptions;
                const consumptionData = {
                    labels: networkData.network.timesteps,
                    datasets: [{
                        label: loadId,
                        data: consumption,
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }]
                };
                loadChart = new Chart(ctx, {
                    type: 'line',
                    data: consumptionData,
                    options: chartOptions
                });
                return;
            }
        }
    }

    function renderStorageChart(storageId) {

        if (generatorChart) generatorChart.destroy(); // prevent duplicate overlays
        if (busChart) busChart.destroy();
        if (storageChart) storageChart.destroy();
        if (loadChart) loadChart.destroy();

        const ctx = document.getElementById('flow-chart').getContext('2d');
        
        for (let bus in networkData.network.buses) {
            const busData = networkData.network.buses[bus]; 
            if (busData.storage_units && busData.storage_units[storageId]) {
                const storageData = busData.storage_units[storageId];
                const charge_inflows = storageData.charge_inflows
                const discharge_outflows = storageData.discharge_outflows
                const consumptions = storageData.consumptions.map(v => -v)

                storageChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: networkData.network.timesteps,
                        datasets: [
                            {
                                label: storageId + " Charge",
                                data: charge_inflows,
                                backgroundColor: 'rgba(75, 192, 192, 0.7)',
                                stack: 'storage'
                            },
                            {
                                label: storageId + " Discharge",
                                data: discharge_outflows.map(v => -v),
                                backgroundColor: 'rgba(99, 169, 255, 0.7)',
                                stack: 'storage'
                            },
                            {
                                label: storageId + " Consumption",
                                data: consumptions,
                                backgroundColor: 'rgba(255, 0, 55, 0.7)',
                                stack: 'storage'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            x: {
                                stacked: true
                            },
                            y: {
                                stacked: true,
                                title: {
                                    display: true,
                                    text: 'Power (MW)'
                                },
                                grid: {
                                    drawBorder: true,
                                    drawOnChartArea: true,
                                    drawTicks: true,
                                    color: (context) => {
                                        if (context.tick.value === 0) return '#333'; // thicker or darker line for y=0
                                        return 'rgba(0,0,0,0.1)';
                                    },
                                    lineWidth: (context) => {
                                        return context.tick.value === 0 ? 2 : 1;
                                    }
                                }
                            }   
                        },
                        plugins: {
                            title: {
                                display: true,
                                text: `Storage flows for ${storageId}`
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false
                            },
                            legend: {
                                position: 'right',
                                align: 'start',
                                labels: {
                                    boxWidth: 15,
                                    padding: 15
                                }
                            }
                        }
                    }
                });
                return;
            }

        }
    }



    // Initialize with graph popup hidden
    hideGraphPopup();
});
