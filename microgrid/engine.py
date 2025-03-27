from pulp import LpMinimize, LpProblem, LpVariable, lpSum, LpStatus
from graphviz import Digraph

class Network:
    def __init__(self):
        self.buses = []
        self.transmission_lines = {}
        self.solved = False

    def add_bus(self, bus):
        self.buses.append(bus)
        bus.network = self

    def add_transmission_line(self, transmission_line):
        transmission_line.network = self
        self.transmission_lines[(transmission_line.start_bus, transmission_line.end_bus)] = transmission_line

    def solve(self):
        self.model = LpProblem("Energy_Planning", LpMinimize)

        # Generator capacity constraints
        for bus in self.buses:
            for generator in bus.generators:
                self.model += generator.output <= generator.capacity, f"Generator_Capacity_{generator.name}"

        # Transmission Line Constraints
        for line in self.transmission_lines.values():
            self.model += line.flow <= line.capacity, f"Transmission_Line_Capacity_Max_{line.name}"
            self.model += line.flow >= -line.capacity, f"Transmission_Line_Capacity_Min_{line.name}"


        # Energy Balance: Generation + Imports = Demand + Exports
        energy_balance_constraints = {}
        for bus in self.buses:
            constraint = (
                lpSum(g.output for g in bus.generators)
                + lpSum([t.flow for t in bus.get_lines_flowing_in()])
                - lpSum([t.flow for t in bus.get_lines_flowing_out()])
                == bus.demand
            )
            self.model += constraint, f"Energy_Balance_{bus.name}"
            energy_balance_constraints[bus] = constraint

        # --- Define Objective Function ---
        self.model += lpSum(g.cost * g.output for b in self.buses for g in b.generators)

        # Solve the model
        self.model.solve()

        # Extract nodal prices
        nodal_prices = {}
        for bus, constraint in energy_balance_constraints.items():
            bus.nodal_price = self.model.constraints[constraint.name].pi  # Extract shadow price
        print(f"Solution: {LpStatus[self.model.status]}")
        return LpStatus[self.model.status]


    def draw_network(self):
        dot = Digraph(comment='Energy Network')
        dot.graph_attr['rankdir'] = 'LR'
        for b in self.buses:
            dot.node(b.name, label=f"{b.name}: {b.demand}MW \n {b.nodal_price} £/MWh", shape='polygon')
            for g in b.generators:
                dot.node(g.name, label=f"{g.name}: £{g.cost}/MWh")
                dot.edge(g.name, b.name, label=f"{g.output.varValue} / {g.capacity}")
        for t in self.transmission_lines.values():
            if t.flow.varValue > 0:
                dot.edge(t.start_bus.name, t.end_bus.name,
                        label=f"{t.flow.varValue} / {t.capacity}", color='blue', fontcolor='blue')
            else:
                dot.edge(t.end_bus.name, t.start_bus.name,
                        label=str(-t.flow.varValue), color='blue', fontcolor='blue')
        return dot


class Bus:
    def __init__(self, name, demand):
        self.name = name
        self.generators = []
        self.demand = demand
        self.network = None

    def add_generator(self, generator):
        self.generators.append(generator)
        generator.bus = self

    def get_lines_flowing_in(self):
        return [line for line in self.network.transmission_lines.values() if line.end_bus == self]

    def get_lines_flowing_out(self):
        return [line for line in self.network.transmission_lines.values() if line.start_bus == self]


class TransmissionLine:
    def __init__(self,start_bus, end_bus, capacity):
        self.name = f"{start_bus.name}_to_{end_bus.name}"
        self.start_bus = start_bus
        self.end_bus = end_bus
        self.capacity = capacity
        self.flow = LpVariable(f"{self.name}_flow", -self.capacity, self.capacity)

    def __repr__(self):
        return f"{self.name} - Start: {self.start_bus.name} - End: {self.end_bus.name} - Capacity: {self.capacity} - Flow: {self.flow.varValue}"

class Generator:
    def __init__(self, name, capacity, cost):
        self.name = name
        self.capacity = capacity
        self.cost = cost
        self.output = LpVariable(f"{self.name}_output", 0, self.capacity)
        self.bus = None

    def __repr__(self):
        return f"{self.name} - Capacity: {self.capacity} - Cost: {self.cost} - Output: {self.output.varValue}"