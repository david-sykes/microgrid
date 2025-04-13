from microgrid.engine import Network, Bus, Generator, TransmissionLine, Load, StorageUnit, EVFleet
from microgrid.draw import draw_network


# Setup 1st bus

n = Network(name='EVFleet', timesteps=[1, 2, 3, 4, 5])

b1 = Bus(name='National node', network=n)
g = Generator('G', capacities=[100, 0, 0, 100, 0], costs=[0]*5, bus=b1)
evf = EVFleet('EVs', bus=b1, max_soc_capacity=100, min_soc_requirements_start_of_ts=[20]*5, max_charge_capacities=[10]*5, max_discharge_capacities=[10]*5, mwh_per_km_driven=0.3/1000,
                km_driven=[10_000, 0, 10_000, 0, 0]
)

status = n.solve()

for ts in n.timesteps:
    dot = draw_network(n, ts)
    dot.render(f"examples/outputs/{n.name.replace(' ', '-')}_{ts}", format='png')