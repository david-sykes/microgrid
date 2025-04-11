from pulp import LpMinimize, LpProblem, LpVariable, lpSum, LpStatus

class TimestepLengthMismatch(Exception):
    """Raised when the length of timesteps does not match other time-dependent data."""
    pass


class Network:
    def __init__(self, name: str, timesteps: list):
        self.name = name
        self.buses = []
        self.transmission_lines = []
        self.solved = False
        self.timesteps = timesteps
        self.timestep_index = {label: i for i, label in enumerate(self.timesteps)}


    def add_bus(self, bus):
        self.buses.append(bus)
        bus.network = self
        bus.nodal_prices = [None] * len(self.timesteps)
        
        # Generators
        for g in bus.generators:
            g.outputs = []
            for ts, capacity in zip(self.timesteps, g.capacities):
                g.outputs.append(LpVariable(f"{g.name}_output_{ts}", 0, capacity))
        
        # Storage
        for su in bus.storage_units:
            su.charge_inflows = [] #Always positive
            su.discharge_outflows = [] #Always positive
            su.socs_start_of_ts = []
            su.socs_end_of_ts = []
            for i, ts in enumerate(self.timesteps):
                su.charge_inflows.append(
                    LpVariable(f"{su.name}_charge_inflows_{ts}", 
                    0,
                    su.max_charge_capacities[i]))
                su.discharge_outflows.append(
                    LpVariable(f"{su.name}_discharge_outflows_{ts}", 
                    0,
                    su.max_discharge_capacities[i]))
                su.socs_start_of_ts.append(LpVariable(f"{su.name}_soc_start_of_{ts}", 0, su.max_soc_capacity))
                su.socs_end_of_ts.append(LpVariable(f"{su.name}_soc_end_of_{ts}", 0, su.max_soc_capacity))

        # EV Fleets
        for evf in bus.ev_fleets:
            evf.charge_inflows = [] #Always positive
            evf.discharge_outflows = [] #Always positive
            evf.socs_start_of_ts = []
            evf.socs_end_of_ts = []
            for i, ts in enumerate(self.timesteps):
                evf.charge_inflows.append(
                    LpVariable(f"{evf.name}_charge_inflows_{ts}", 
                    0,
                    evf.max_charge_capacities[i]))
                evf.discharge_outflows.append(
                    LpVariable(f"{evf.name}_discharge_outflows_{ts}", 
                    0,
                    evf.max_discharge_capacities[i]))
                evf.socs_start_of_ts.append(LpVariable(f"{evf.name}_soc_start_of_{ts}", 0, evf.max_soc_capacity))
                evf.socs_end_of_ts.append(LpVariable(f"{evf.name}_soc_end_of_{ts}", 0, evf.max_soc_capacity))


    def add_transmission_line(self, transmission_line):
        transmission_line.network = self
        transmission_line.flows = []
        for ts, capacity in zip(self.timesteps, transmission_line.capacities):
            transmission_line.flows.append(
                LpVariable(f"{transmission_line.name}_flow_{ts}", -capacity, capacity)
            )
        self.transmission_lines.append(transmission_line)

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
            for ev_fleet in b.ev_fleets:
                if len(ev_fleet.km_driven) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"EV fleet miles driven timesteps do not match network timesteps for {ev_fleet.name}")
                if len(ev_fleet.max_charge_capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"EV fleet charge capacity timesteps do not match network timesteps for {ev_fleet.name}")
                if len(ev_fleet.max_discharge_capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"EV fleet discharge capacity timesteps do not match network timesteps for {ev_fleet.name}")
                    


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
                    self.model += su.charge_inflows[i] <= su.max_charge_capacities[i], f"Storage_charge_inflows_Max_{su.name}_{ts}"
                    self.model += su.discharge_outflows[i] <= su.max_discharge_capacities[i], f"Storage_discharge_outflows_Min_{su.name}_{ts}"

                    # Storage unit SOC can't be more than max capacity or less than zero
                    self.model += su.socs_start_of_ts[i] <= su.max_soc_capacity, f"Storage_SOC_Max_{su.name}_start_of_{ts}"
                    self.model += su.socs_start_of_ts[i] >= 0, f"Storage_SOC_Min_{su.name}_start_of_{ts}" # Storage SOC at end is zero - only needs doing once
                    self.model += su.socs_end_of_ts[i] <= su.max_soc_capacity, f"Storage_SOC_Max_{su.name}_end_of_{ts}"
                    self.model += su.socs_end_of_ts[i] >= 0, f"Storage_SOC_Min_{su.name}_end_of_{ts}" # Storage SOC at end is zero - only needs doing once

                    # SOC and charge/discharge balance
                    self.model += su.socs_end_of_ts[i] == su.socs_start_of_ts[i]\
                                            + su.charge_efficiency * su.charge_inflows[i]\
                                            - (1 / su.discharge_efficiency) * su.discharge_outflows[i],\
                                            f"Storage_SOC_charge_balance_{su.name}_{ts}"
                    
                    # Continuity of SOC
                    if i < len(self.timesteps) - 1:
                        self.model += su.socs_start_of_ts[i+1] == su.socs_end_of_ts[i], f"Storage_SOC_continuity_{su.name}_{ts}"

        # EV Fleet Constraints
        for bus in self.buses:
            for evf in bus.ev_fleets:
                self.model += evf.socs_start_of_ts[0] == evf.min_soc_requirements_start_of_ts[0], f"EVFleet_SOC_Start_{evf.name}" # Storage SOC at start is the min requirement for that timestep - only needs doing once
                self.model += evf.socs_end_of_ts[-1] == evf.min_soc_requirements_start_of_ts[-1], f"EVFleet_SOC_End_{evf.name}" # Storage SOC at end is the min requirement for that timestep - only needs doing once
            
            for i, ts in enumerate(self.timesteps):
                # EV Fleet can't charge or discharge more than its max charge/discharge capacity
                self.model += evf.charge_inflows[i] <= evf.max_charge_capacities[i], f"EVFleet_charge_inflows_Max_{evf.name}_{ts}"
                self.model += evf.discharge_outflows[i] <= evf.max_discharge_capacities[i], f"EVFleet_discharge_outflows_Min_{evf.name}_{ts}"

                # EV Fleet SOC can't be more than max capacity or less than zero
                self.model += evf.socs_start_of_ts[i] <= evf.max_soc_capacity, f"EVFleet_SOC_Max_{evf.name}_start_of_{ts}"
                self.model += evf.socs_start_of_ts[i] >= evf.min_soc_requirements_start_of_ts[i], f"EVFleet_SOC_Min_{evf.name}_start_of_{ts}" # Storage SOC must be above the min requirement for that timestep
                self.model += evf.socs_end_of_ts[i] <= evf.max_soc_capacity, f"EVFleet_SOC_Max_{evf.name}_end_of_{ts}"
                self.model += evf.socs_end_of_ts[i] >= 0, f"EVFleet_SOC_Min_{evf.name}_end_of_{ts}" # Storage SOC must be above zero

                # SOC and charge/discharge balance
                self.model += evf.socs_end_of_ts[i] == evf.socs_start_of_ts[i]\
                                        + evf.charge_efficiency * evf.charge_inflows[i]\
                                        - (1 / evf.discharge_efficiency) * evf.discharge_outflows[i]\
                                        - (evf.km_driven[i]*evf.mwh_per_km_driven),\
                                        f"EVFleet_SOC_charge_balance_{evf.name}_{ts}"
                
                # Continuity of SOC
                if i < len(self.timesteps) - 1:
                    self.model += evf.socs_start_of_ts[i+1] == evf.socs_end_of_ts[i], f"EVFleet_SOC_continuity_{evf.name}_{ts}"

        # Transmission Line Constraints
        for line in self.transmission_lines:
            for i, ts in enumerate(self.timesteps):
                self.model += line.flows[i] <= line.capacities[i], f"Transmission_Line_Capacity_Max_{line.name}_{ts}"
                self.model += line.flows[i] >= -line.capacities[i], f"Transmission_Line_Capacity_Min_{line.name}_{ts}"

                    

        # Energy Balance: Generation + Imports = Demand + Exports
        energy_balance_constraints = []
        for i, ts in enumerate(self.timesteps):
            energy_balance_constraints_ts = {}
            for bus in self.buses:
                constraint = (
                    # Flows into node
                    lpSum(g.outputs[i] for g in bus.generators)
                    + lpSum([t.flows[i] for t in bus.get_lines_flowing_in()])
                    + lpSum(su.discharge_outflows[i] for su in bus.storage_units)
                    + lpSum(evf.discharge_outflows[i] for evf in bus.ev_fleets)
                    == 
                    # Flows out of node
                    lpSum(l.demands[i] for l in bus.loads) 
                    + lpSum(su.charge_inflows[i] for su in bus.storage_units)
                    + lpSum([t.flows[i] for t in bus.get_lines_flowing_out()])
                    + lpSum(evf.charge_inflows[i] for evf in bus.ev_fleets)
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
    def __init__(self, name, max_soc_capacity, max_charge_capacities, max_discharge_capacities, charge_efficiency=0.95, discharge_efficiency=0.95):
        self.name = name
        self.max_soc_capacity = max_soc_capacity
        self.max_charge_capacities = max_charge_capacities
        self.max_discharge_capacities = max_discharge_capacities
        self.charge_efficiency = charge_efficiency #This is defined as energy stored / energy imported from grid 
        self.discharge_efficiency = discharge_efficiency #This is defined as energy exported / energy stored
    
    def __repr__(self):
        return f"{self.name} - Max SOC Capacity: {self.max_soc_capacity} - Max Charge Capacities: {self.max_charge_capacities} - Max Discharge Capacities: {self.max_discharge_capacities}"
    
class EVFleet:
    """Represents conventional EVs, as well as V2G EVs"""
    def __init__(self, name, max_soc_capacity, min_soc_requirements_start_of_ts: list,
                    max_charge_capacities: list, max_discharge_capacities: list,
                    km_driven: list, mwh_per_km_driven=0.3/1000,
                    charge_efficiency=0.95, discharge_efficiency=0.95):
        self.name = name
        self.max_soc_capacity = max_soc_capacity
        self.min_soc_requirements_start_of_ts = min_soc_requirements_start_of_ts
        self.max_charge_capacities = max_charge_capacities
        self.max_discharge_capacities = max_discharge_capacities
        self.charge_efficiency = charge_efficiency #This is defined as energy stored / energy imported from grid 
        self.discharge_efficiency = discharge_efficiency #This is defined as energy exported / energy stored
        self.km_driven = km_driven # A list of the miles driven in each simulation period
        self.mwh_per_km_driven = mwh_per_km_driven # The amount of energy consumed per km driven
        self.bus = None
        

class Bus:
    def __init__(self, name):
        self.name = name
        self.generators = []
        self.loads = []
        self.storage_units = []
        self.network = None
        self.nodal_prices = []
        self.ev_fleets = []

    def add_generator(self, generator: Generator):
        self.generators.append(generator)
        generator.bus = self

    def add_load(self, load: Load):
        self.loads.append(load)
        load.bus = self

    def add_storage_unit(self, storage_unit: StorageUnit):
        self.storage_units.append(storage_unit)
        storage_unit.bus = self

    def add_ev_fleet(self, ev_fleet: EVFleet):
        self.ev_fleets.append(ev_fleet)
        ev_fleet.bus = self

    def get_lines_flowing_in(self):
        return [line for line in self.network.transmission_lines if line.end_bus == self]

    def get_lines_flowing_out(self):
        return [line for line in self.network.transmission_lines if line.start_bus == self]