from microgrid.engine import Network, Bus, Generator, TransmissionLine
import os

# Setup 1st bus
b1 = Bus(name='North', demands=[40, 40, 40])
Ng1 = Generator('N_Gas', capacities=[50, 50, 50], costs=[50, 50, 50])
Ng2 = Generator('N_Wind', capacities=[100, 50, 0], costs=[0, 0, 0])
b1.add_generator(Ng1)
b1.add_generator(Ng2)

# Setup 2nd bus
b2 = Bus('South', demands=[100, 100, 100])
Sg1 = Generator('S_Gas', capacities=[100, 100, 100], costs=[100, 100, 100])
b2.add_generator(Sg1)

# Initialise network and add buses
n = Network(name='Simple 3 Node', timesteps=[1,2,3])
n.add_bus(b1)
n.add_bus(b2)

# Connect buses
t = TransmissionLine(start_bus=b1, end_bus=b2, capacities=[50,50,50])
n.add_transmission_line(t)

#Solve and draw
status = n.solve()


for ts in n.timesteps:
    dot = n.draw_network(timestep=ts)
    dot.render(f"examples/outputs/{n.name.replace(' ', '-')}_{ts}", format='png')