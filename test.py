from microgrid.engine import Network, Bus, Generator, Load
from microgrid.save import save_network
from microgrid.draw import draw_network

# Create a network with two timesteps
timesteps = ['morning', 'evening']
network = Network("SimpleGrid", timesteps)

# Create a bus (electrical node)
bus = Bus("MainBus", network)

# Add generators with different costs
Generator("CheapGen", capacities=[10, 10], costs=[5, 5], bus=bus)
Generator("ExpensiveGen", capacities=[15, 15], costs=[10, 10], bus=bus)

# Add electrical load
Load("CityLoad", consumptions=[12, 8], bus=bus)

# Solve the optimization
status = network.solve()
print(f"Solution status: {status}")

# Check results
for gen_name, gen in bus.generators.items():
    print(f"{gen_name} outputs: {[out.varValue for out in gen.outputs]}")

print(f"Nodal prices: {bus.nodal_prices}")

# Save network
save_network(network, "simple_grid.json", "simple_grid.db")

# Draw network
dot = draw_network(network, "morning")
dot.render("simple_grid", format='png')