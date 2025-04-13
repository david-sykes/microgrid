from microgrid.engine import Network, Bus, Generator, TransmissionLine, Load, StorageUnit
from microgrid.draw import draw_network


# Setup 1st bus
b1 = Bus(name='North node')
l1 = Load('N_domestic', consumptions=[50])
Ng1 = Generator('N_Wind', capacities=[100], costs=[0])

b1.add_generator(Ng1)
b1.add_load(l1)

b2 = Bus(name='South node')

# Setup 2nd bus
l2 = Load('S_domestic', consumptions=[100])

Sg1 = Generator('S_Gas', capacities=[50], costs=[100])
Sg2 = Generator('S_Nuclear', capacities=[50], costs=[10])

b2.add_generator(Sg1)
b2.add_generator(Sg2)
b2.add_load(l2)

# Initialise network and add buses
n = Network(name='2 node', timesteps=[1])
n.add_bus(b1)
n.add_bus(b2)

# Connect buses
t = TransmissionLine(start_bus=b1, end_bus=b2, capacities=[30])
n.add_transmission_line(t)

status = n.solve()

for ts in n.timesteps:
    dot = draw_network(n, ts)
    dot.render(f"examples/outputs/{n.name.replace(' ', '-')}_{ts}", format='png')