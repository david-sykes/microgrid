from pulp import LpMinimize, LpProblem, LpVariable, lpSum, LpStatus

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
        for su in bus.storage_units:
            su.net_inflows = []
            su.socs_start_of_ts = []
            su.socs_end_of_ts = []
            for i, ts in enumerate(self.timesteps):
                su.net_inflows.append(
                    LpVariable(f"{su.name}_net_inflows_{ts}", 
                    -su.max_discharge_capacities[i],
                    su.max_charge_capacities[i]))
                su.socs_start_of_ts.append(LpVariable(f"{su.name}_soc_start_of_{ts}", 0, su.max_soc_capacity))
                su.socs_end_of_ts.append(LpVariable(f"{su.name}_soc_end_of_{ts}", 0, su.max_soc_capacity))
                

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
            for l in b.loads:
                if len(l.demands) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Demand timesteps do not match network timesteps for {b.name}")
            for g in b.generators:
                if len(g.capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Generator capacity timesteps do not match network timesteps for {g.name}")
                if len(g.costs) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Generator cost timesteps do not match network timesteps for {g.name}")
            for su in b.storage_units:
                if len(su.max_charge_capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Storage unit charge capacity timesteps do not match network timesteps for {su.name}")
                if len(su.max_discharge_capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Storage unit discharge capacity timesteps do not match network timesteps for {su.name}")


        # Generator capacity constraints
        for bus in self.buses:
            for generator in bus.generators:
                for i, ts in enumerate(self.timesteps):
                    self.model += generator.outputs[i] <= generator.capacities[i], f"Generator_Capacity_{generator.name}_{ts}"

        # Storage Unit Constraints
        for bus in self.buses:
            
            for su in bus.storage_units:
                self.model += su.socs_start_of_ts[0] == 0, f"Storage_SOC_Start_{su.name}" # Storage SOC at start is zero - only needs doing once
                self.model += su.socs_end_of_ts[-1] == 0, f"Storage_SOC_End_{su.name}" # Storage SOC at end is zero - only needs doing once

                for i, ts in enumerate(self.timesteps):
                    # Storage unit can't inflow or outflow more than it's max charge/discharge capacity
                    self.model += su.net_inflows[i] <= su.max_charge_capacities[i], f"Storage_netinflow_Max_{su.name}_{ts}"
                    self.model += su.net_inflows[i] >= -su.max_discharge_capacities[i], f"Storage_netinflow_Min_{su.name}_{ts}"

                    # Storage unit SOC can't be more than max capacity or less than zero
                    self.model += su.socs_start_of_ts[i] <= su.max_soc_capacity, f"Storage_SOC_Max_{su.name}_start_of_{ts}"
                    self.model += su.socs_start_of_ts[i] >= 0, f"Storage_SOC_Min_{su.name}_start_of_{ts}" # Storage SOC at end is zero - only needs doing once
                    self.model += su.socs_end_of_ts[i] <= su.max_soc_capacity, f"Storage_SOC_Max_{su.name}_end_of_{ts}"
                    self.model += su.socs_end_of_ts[i] >= 0, f"Storage_SOC_Min_{su.name}_end_of_{ts}" # Storage SOC at end is zero - only needs doing once

                    self.model += su.socs_end_of_ts[i] == su.socs_start_of_ts[i] + su.net_inflows[i], f"Storage_SOC_charge_balance_{su.name}_{ts}"
                    if i < len(self.timesteps) - 1:
                        self.model += su.socs_start_of_ts[i+1] == su.socs_end_of_ts[i], f"Storage_SOC_continuity_{su.name}_{ts}"


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
                    == lpSum(l.demands[i] for l in bus.loads) + lpSum(su.net_inflows[i] for su in bus.storage_units)
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

class Load:
    def __init__(self, name, demands: list):
        self.name = name
        self.demands = demands
        self.bus = None

    def __repr__(self):
        output_info = [f"{output.varValue if output else 'None'}" for output in self.outputs]
        return f"{self.name} - Capacities: {self.capacities} - Costs: {self.costs} - Outputs: {output_info}"

class StorageUnit:
    def __init__(self, name, max_soc_capacity, max_charge_capacities, max_discharge_capacities):
        self.name = name
        self.max_soc_capacity = max_soc_capacity
        self.max_charge_capacities = max_charge_capacities
        self.max_discharge_capacities = max_discharge_capacities
    
    def __repr__(self):
        return f"{self.name} - Max SOC Capacity: {self.max_soc_capacity} - Max Charge Capacities: {self.max_charge_capacities} - Max Discharge Capacities: {self.max_discharge_capacities}"
    
    
        

class Bus:
    def __init__(self, name):
        self.name = name
        self.generators = []
        self.loads = []
        self.storage_units = []
        self.network = None
        self.nodal_prices = []

    def add_generator(self, generator: Generator):
        self.generators.append(generator)
        generator.bus = self

    def add_load(self, load: Load):
        self.loads.append(load)
        load.bus = self

    def add_storage_unit(self, storage_unit: StorageUnit):
        self.storage_units.append(storage_unit)
        storage_unit.bus = self

    def get_lines_flowing_in(self):
        return [line for line in self.network.transmission_lines.values() if line.end_bus == self]

    def get_lines_flowing_out(self):
        return [line for line in self.network.transmission_lines.values() if line.start_bus == self]