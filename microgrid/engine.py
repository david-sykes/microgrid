from pulp import LpMinimize, LpProblem, LpVariable, lpSum, LpStatus
from graphviz import Digraph

class TimestepLengthMismatch(Exception):
    """Raised when the length of timesteps does not match other time-dependent data."""
    pass


class Network:
    def __init__(self, name: str, timesteps: list):
        self.name = name
        self.buses = []
        self.transmission_lines = {}
        self.solved = False
        self.timesteps = timesteps
        self.timestep_index = {label: i for i, label in enumerate(self.timesteps)}


    def add_bus(self, bus):
        self.buses.append(bus)
        bus.network = self
        bus.nodal_prices = [None] * len(self.timesteps)
        for g in bus.generators:
            g.outputs = []
            for ts, capacity in zip(self.timesteps, g.capacities):
                g.outputs.append(LpVariable(f"{g.name}_output_{ts}", 0, capacity))
            

    def add_transmission_line(self, transmission_line):
        transmission_line.network = self
        transmission_line.flows = []
        for ts, capacity in zip(self.timesteps, transmission_line.capacities):
            transmission_line.flows.append(
                LpVariable(f"{transmission_line.name}_flow_{ts}", -capacity, capacity)
            )
        self.transmission_lines[(transmission_line.start_bus, transmission_line.end_bus)] = transmission_line

    def solve(self):
        # For now we solve the network for all timesteps as one problem
        self.model = LpProblem("Energy_Planning", LpMinimize)

        # Check timesteps match accross all components
        print("Checking timesteps match accross all components")

        for b in self.buses:
            if len(b.demands) != len(self.timesteps):
                raise TimestepLengthMismatch(f"Demand timesteps do not match network timesteps for {b.name}")
            for g in b.generators:
                if len(g.capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Generator capacity timesteps do not match network timesteps for {g.name}")
                if len(g.costs) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Generator cost timesteps do not match network timesteps for {g.name}")

        # Generator capacity constraints
        for bus in self.buses:
            for generator in bus.generators:
                for i, ts in enumerate(self.timesteps):
                    self.model += generator.outputs[i] <= generator.capacities[i], f"Generator_Capacity_{generator.name}_{ts}"
                

        # Transmission Line Constraints
        for line in self.transmission_lines.values():
            for i, ts in enumerate(self.timesteps):
                self.model += line.flows[i] <= line.capacities[i], f"Transmission_Line_Capacity_Max_{line.name}_{ts}"
                self.model += line.flows[i] >= -line.capacities[i], f"Transmission_Line_Capacity_Min_{line.name}_{ts}"


        # Energy Balance: Generation + Imports = Demand + Exports
        energy_balance_constraints = []
        for i, ts in enumerate(self.timesteps):
            energy_balance_constraints_ts = {}
            for bus in self.buses:
                constraint = (
                    lpSum(g.outputs[i] for g in bus.generators)
                    + lpSum([t.flows[i] for t in bus.get_lines_flowing_in()])
                    - lpSum([t.flows[i] for t in bus.get_lines_flowing_out()])
                    == bus.demands[i]
                )
                self.model += constraint, f"Energy_Balance_{bus.name}_{ts}"
                energy_balance_constraints_ts[bus] = constraint
            energy_balance_constraints.append(energy_balance_constraints_ts)

        # --- Define Objective Function ---
        self.model += lpSum(
            g.costs[i] * g.outputs[i]
            for i, t in enumerate(self.timesteps)
            for b in self.buses
            for g in b.generators
        ), "Total_Cost"

        # Solve the model
        self.model.solve()

        # Extract nodal prices
        for i, ts in enumerate(self.timesteps):
            energy_balance_constraints_ts = energy_balance_constraints[i]
            for bus, constraint in energy_balance_constraints_ts.items():
                bus.nodal_prices[i] = self.model.constraints[constraint.name].pi  # Extract shadow price
        print(f"Solution: {LpStatus[self.model.status]}")
        return LpStatus[self.model.status]


    def draw_network(self, timestep):
        timestep_index = self.timestep_index[timestep]
        dot = Digraph(comment='Energy Network')
        dot.graph_attr['rankdir'] = 'LR'
        for b in self.buses:
            dot.node(b.name, label=f"{b.name}: {b.demands[timestep_index]}MW \n {b.nodal_prices[timestep_index]} £/MWh", shape='polygon')
            for g in b.generators:
                dot.node(g.name, label=f"{g.name}: £{g.costs[timestep_index]}/MWh")
                dot.edge(g.name, b.name, label=f"{g.outputs[timestep_index].varValue} / {g.capacities[timestep_index]}")
        for t in self.transmission_lines.values():
            if t.flows[timestep_index].varValue > 0:
                dot.edge(t.start_bus.name, t.end_bus.name,
                        label=f"{t.flows[timestep_index].varValue} / {t.capacities[timestep_index]}", color='blue', fontcolor='blue')
            else:
                dot.edge(t.end_bus.name, t.start_bus.name,
                        label=str(-t.flows[timestep_index].varValue), color='blue', fontcolor='blue')
        return dot


class Bus:
    def __init__(self, name, demands: list):
        self.name = name
        self.generators = []
        self.demands = demands
        self.network = None
        self.nodal_prices = []

    def add_generator(self, generator):
        self.generators.append(generator)
        generator.bus = self

    def get_lines_flowing_in(self):
        return [line for line in self.network.transmission_lines.values() if line.end_bus == self]

    def get_lines_flowing_out(self):
        return [line for line in self.network.transmission_lines.values() if line.start_bus == self]


class TransmissionLine:
    def __init__(self,start_bus, end_bus, capacities: list):
        self.name = f"{start_bus.name}_to_{end_bus.name}"
        self.start_bus = start_bus
        self.end_bus = end_bus
        self.capacities = capacities
        self.flows = None

    def __repr__(self):
        flow_info = [f"{flow.varValue if flow else 'None'}" for flow in self.flows]
        return f"{self.name} - Start: {self.start_bus.name} - End: {self.end_bus.name} - Capacities: {self.capacities} - Flows: {flow_info}"

class Generator:
    def __init__(self, name, capacities: list, costs: list):
        self.name = name
        self.capacities = capacities
        self.costs = costs
        self.bus = None

    def __repr__(self):
        output_info = [f"{output.varValue if output else 'None'}" for output in self.outputs]
        return f"{self.name} - Capacities: {self.capacities} - Costs: {self.costs} - Outputs: {output_info}"