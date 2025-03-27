from microgrid.engine import Network, Bus, Generator, TransmissionLine
import os

# Setup 1st bus
b1 = Bus(name='North', demand=40)
Ng1 = Generator('N_Gas', capacity=20, cost=50)
Ng2 = Generator('N_Wind', capacity=50, cost=10)
b1.add_generator(Ng1)
b1.add_generator(Ng2)

# Setup 2nd bus
b2 = Bus('South', demand=100)
Sg1 = Generator('S_Gas', capacity=100, cost=100)
b2.add_generator(Sg1)

# Initialise network and add buses
n = Network()
n.add_bus(b1)
n.add_bus(b2)

# Connect buses
t = TransmissionLine(start_bus=b1, end_bus=b2, capacity=5)
n.add_transmission_line(t)

#Solve and draw
status = n.solve()

dot = n.draw_network()
dot.render("examples/outputs/network_diagram.", format='png')