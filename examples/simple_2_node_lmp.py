from microgrid.engine import Network, Bus, Generator, TransmissionLine, Load, StorageUnit
from microgrid.draw import draw_network

import os

# Setup 1st bus
b1 = Bus(name='North')
l1 = Load('N_domestic', demands=[10, 40, 40])
Ng1 = Generator('N_Gas', capacities=[50, 50, 50], costs=[50, 50, 50])
Ng2 = Generator('N_Wind', capacities=[100, 50, 0], costs=[0, 0, 0])
Nsu1 = StorageUnit('N_battery', max_soc_capacity=100, max_charge_capacities=[10, 10, 10], max_discharge_capacities=[10, 10, 10])

b1.add_generator(Ng1)
b1.add_generator(Ng2)
b1.add_load(l1)
b1.add_storage_unit(Nsu1)


# Setup 2nd bus
b2 = Bus('South')
l2 = Load('S_domestic', demands=[100, 50, 100])

Sg1 = Generator('S_Gas', capacities=[100, 100, 100], costs=[100, 100, 100])

b2.add_generator(Sg1)
b2.add_load(l2)


# Initialise network and add buses
n = Network(name='Simple 2 Node', timesteps=[1,2,3])
n.add_bus(b1)
n.add_bus(b2)

# Connect buses
t = TransmissionLine(start_bus=b1, end_bus=b2, capacities=[50,50,50])
n.add_transmission_line(t)

#Solve and draw
status = n.solve()
    

for ts in n.timesteps:
    dot = draw_network(n, ts)
    dot.render(f"examples/outputs/{n.name.replace(' ', '-')}_{ts}", format='png')