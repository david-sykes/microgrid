from microgrid.engine import Network, Bus, Generator, TransmissionLine, Load, StorageUnit, EVFleet
from microgrid.draw import draw_network


# Setup 1st bus
b1 = Bus(name='National node')
g = Generator('G', capacities=[100, 0, 0, 100, 0], costs=[0]*5)
evf = EVFleet('EVs', max_soc_capacity=100, min_soc_requirements_start_of_ts=[20]*5, max_charge_capacities=[10]*5, max_discharge_capacities=[10]*5, mwh_per_km_driven=0.3/1000,
                km_driven=[10_000, 0, 10_000, 0, 0]
)
b1.add_generator(g)
b1.add_ev_fleet(evf)

# Initialise network and add buses
n = Network(name='EVFleet', timesteps=[1, 2, 3, 4, 5])
n.add_bus(b1)

status = n.solve()

for ts in n.timesteps:
    dot = draw_network(n, ts)
    dot.render(f"examples/outputs/{n.name.replace(' ', '-')}_{ts}", format='png')