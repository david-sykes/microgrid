from microgrid.engine import Network, Bus, Generator, TransmissionLine, Load, StorageUnit
from microgrid.draw import draw_network

import os

n = Network(name='Simple 2 Node', timesteps=[1,2,3])


# Setup 1st bus
b1 = Bus(name='North', network=n)
l1 = Load('N_domestic', demands=[10, 40, 40], bus=b1)
Ng1 = Generator('N_Gas', capacities=[50, 50, 50], costs=[50, 50, 50], bus=b1)
Ng2 = Generator('N_Wind', capacities=[100, 50, 0], costs=[0, 0, 0], bus=b1)
Nsu1 = StorageUnit('N_battery', bus=b1, max_soc_capacity=100, max_charge_capacities=[10, 10, 10], max_discharge_capacities=[10, 10, 10])

# Setup 2nd bus
b2 = Bus('South', network=n)
l2 = Load('S_domestic', demands=[100, 50, 100], bus=b2)

Sg1 = Generator('S_Gas', capacities=[100, 100, 100], costs=[100, 100, 100], bus=b2)

# Connect buses
t = TransmissionLine(start_bus=b1, end_bus=b2, capacities=[50,50,50], network=n)

#Solve and draw
status = n.solve()
    

for ts in n.timesteps:
    dot = draw_network(n, ts)
    dot.render(f"examples/outputs/{n.name.replace(' ', '-')}_{ts}", format='png')