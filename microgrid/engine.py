from pulp import LpMinimize, LpProblem, LpVariable, lpSum, LpStatus

class TimestepLengthMismatch(Exception):
    """Raised when the length of timesteps does not match other time-dependent data."""
    pass


class Network:
    def __init__(self, name: str, timesteps: list):
        self.name = name
        self.buses = {}  
        self.transmission_lines = {}  
        self.solved = False
        self.timesteps = timesteps
        self.timestep_index = {label: i for i, label in enumerate(self.timesteps)}
        

    def solve(self):
        # For now we solve the network for all timesteps as one problem
        self.model = LpProblem("Energy_Planning", LpMinimize)

        # Check timesteps match accross all components
        print("Checking timesteps match accross all components")

        for b in self.buses.values():
            for l in b.loads.values():
                if len(l.consumptions) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Consumption timesteps do not match network timesteps for {b.name}")
            for g in b.generators.values():
                if len(g.capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Generator capacity timesteps do not match network timesteps for {g.name}")
                if len(g.costs) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Generator cost timesteps do not match network timesteps for {g.name}")
            for su in b.storage_units.values():
                if len(su.max_charge_capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Storage unit charge capacity timesteps do not match network timesteps for {su.name}")
                if len(su.max_discharge_capacities) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Storage unit discharge capacity timesteps do not match network timesteps for {su.name}")
                if len(su.min_soc_requirements_start_of_ts) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Storage unit minimum SOC requirements timesteps do not match network timesteps for {su.name}")
                if len(su.consumptions) != len(self.timesteps):
                    raise TimestepLengthMismatch(f"Storage unit consumption timesteps do not match network timesteps for {su.name}")
        for tl in self.transmission_lines.values():
            if len(tl.capacities) != len(self.timesteps):
                raise TimestepLengthMismatch(f"Transmission line capacity timesteps do not match network timesteps for {tl.name}")
                


        # Generator capacity constraints
        for bus in self.buses.values():
            for generator in bus.generators.values():
                for i, ts in enumerate(self.timesteps):
                    self.model += generator.outputs[i] <= generator.capacities[i], f"Generator_Capacity_{generator.name}_{ts}"


        # Storage Unit Constraints
        for bus in self.buses.values():
            
            for su in bus.storage_units.values():
                self.model += su.socs_start_of_ts[0] == su.min_soc_requirements_start_of_ts[0], f"{su.__class__.__name__}_SOC_Start_{su.name}" # Storage SOC at start is zero - only needs doing once
                self.model += su.socs_end_of_ts[-1] == su.min_soc_requirements_start_of_ts[-1], f"{su.__class__.__name__}_SOC_End_{su.name}" # Storage SOC at end is zero - only needs doing once

                for i, ts in enumerate(self.timesteps):
                    # Storage unit can't inflow or outflow more than it's max charge/discharge capacity
                    self.model += su.charge_inflows[i] <= su.max_charge_capacities[i], f"{su.__class__.__name__}_charge_inflows_Max_{su.name}_{ts}"
                    self.model += su.discharge_outflows[i] <= su.max_discharge_capacities[i], f"{su.__class__.__name__}_discharge_outflows_Min_{su.name}_{ts}"

                    # Storage unit SOC can't be more than max capacity or less than zero
                    self.model += su.socs_start_of_ts[i] <= su.max_soc_capacity, f"{su.__class__.__name__}_SOC_Max_{su.name}_start_of_{ts}"
                    self.model += su.socs_start_of_ts[i] >= su.min_soc_requirements_start_of_ts[i], f"Storage_SOC_Min_{su.name}_start_of_{ts}" # Storage SOC must be above min requirements
                    self.model += su.socs_end_of_ts[i] <= su.max_soc_capacity, f"{su.__class__.__name__}_SOC_Max_{su.name}_end_of_{ts}"
                    self.model += su.socs_end_of_ts[i] >= 0, f"{su.__class__.__name__}_SOC_Min_{su.name}_end_of_{ts}" # Storage SOC must be above zero

                    # SOC and charge/discharge balance
                    self.model += su.socs_end_of_ts[i] == su.socs_start_of_ts[i]\
                                            + su.charge_efficiency * su.charge_inflows[i]\
                                            - (1 / su.discharge_efficiency) * su.discharge_outflows[i]\
                                            - su.consumptions[i],\
                                            f"{su.__class__.__name__}_SOC_charge_balance_{su.name}_{ts}"
                    
                    # Continuity of SOC
                    if i < len(self.timesteps) - 1:
                        self.model += su.socs_start_of_ts[i+1] == su.socs_end_of_ts[i], f"{su.__class__.__name__}_SOC_continuity_{su.name}_{ts}"


        # Transmission Line Constraints
        for line in self.transmission_lines.values():
            for i, ts in enumerate(self.timesteps):
                self.model += line.flows[i] <= line.capacities[i], f"Transmission_Line_Capacity_Max_{line.name}_{ts}"
                self.model += line.flows[i] >= -line.capacities[i], f"Transmission_Line_Capacity_Min_{line.name}_{ts}"

                    

        # Energy Balance: Generation + Imports = Demand + Exports
        energy_balance_constraints = []
        for i, ts in enumerate(self.timesteps):
            energy_balance_constraints_ts = {}
            for bus in self.buses.values():
                constraint = (
                    # Flows into node
                    lpSum(g.outputs[i] for g in bus.generators.values())
                    + lpSum([t.flows[i] for t in bus.get_lines_flowing_in()])
                    + lpSum(su.discharge_outflows[i] for su in bus.storage_units.values())
                    == 
                    # Flows out of node
                    lpSum(l.consumptions[i] for l in bus.loads.values()) 
                    + lpSum(su.charge_inflows[i] for su in bus.storage_units.values())
                    + lpSum([t.flows[i] for t in bus.get_lines_flowing_out()])
                )
                self.model += constraint, f"Energy_Balance_{bus.name}_{ts}"
                energy_balance_constraints_ts[bus] = constraint
            energy_balance_constraints.append(energy_balance_constraints_ts)

        # --- Define Objective Function ---
        self.model += lpSum(
            g.costs[i] * g.outputs[i]
            for i, t in enumerate(self.timesteps)
            for b in self.buses.values()
            for g in b.generators.values()
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

class Bus:
    def __init__(self, name, network: Network):
        self.name = name
        self.generators = {}  
        self.loads = {}  
        self.storage_units = {}  
        self.network = network
        self.network.buses[self.name] = self
        self.nodal_prices = [None] * len(self.network.timesteps)

    def get_lines_flowing_in(self):
        return [line for line in self.network.transmission_lines.values() if line.end_bus == self]

    def get_lines_flowing_out(self):
        return [line for line in self.network.transmission_lines.values() if line.start_bus == self]

class TransmissionLine:
    def __init__(self,start_bus, end_bus, capacities: list, network: Network):
        self.name = f"{start_bus.name}_to_{end_bus.name}"
        self.start_bus = start_bus
        self.end_bus = end_bus
        self.capacities = capacities
        self.network = network
        self.network.transmission_lines[self.name] = self  

        #Initialise decision variables
        self.flows = []
        for ts, capacity in zip(self.network.timesteps, self.capacities):
            self.flows.append(LpVariable(f"{self.name}_flow_{ts}", -capacity, capacity))

    
    def __repr__(self):
        flow_info = [f"{flow.varValue if flow else 'None'}" for flow in self.flows]
        return f"{self.name} - Start: {self.start_bus.name} - End: {self.end_bus.name} - Capacities: {self.capacities} - Flows: {flow_info}"

class Generator:
    def __init__(self, name, capacities: list, costs: list, bus: Bus):
        self.name = name
        self.capacities = capacities
        self.costs = costs
        self.bus = bus
        self.bus.generators[self.name] = self  

        # Initialise variables
        self.outputs = []
        for ts, capacity in zip(self.bus.network.timesteps, self.capacities):
            self.outputs.append(LpVariable(f"{self.name}_output_{ts}", 0, capacity))

    def __repr__(self):
        output_info = [f"{output.varValue if output else 'None'}" for output in self.outputs]
        return f"{self.name} - Capacities: {self.capacities} - Costs: {self.costs} - Outputs: {output_info}"

class Load:
    def __init__(self, name, consumptions: list, bus: Bus):
        self.name = name
        self.consumptions = consumptions
        self.bus = bus
        self.bus.loads[self.name] = self

    def __repr__(self):
        output_info = [f"{output.varValue if output else 'None'}" for output in self.outputs]
        return f"{self.name} - Capacities: {self.capacities} - Costs: {self.costs} - Outputs: {output_info}"


class StorageUnit:
    def __init__(
        self,
        name: str,
        bus: Bus,
        max_soc_capacity: float,
        max_charge_capacities: list,
        max_discharge_capacities: list,
        min_soc_requirements_start_of_ts: list,
        consumptions: list, #This is the energy consumed by the storage unit (e.g. if it is modelling EVs)
        charge_efficiency: float = 0.95,
        discharge_efficiency: float = 0.95
    ):
        self.name = name
        self.max_soc_capacity = max_soc_capacity
        self.max_charge_capacities = max_charge_capacities
        self.max_discharge_capacities = max_discharge_capacities
        self.min_soc_requirements_start_of_ts = min_soc_requirements_start_of_ts #The minimum SOC the storage needs at the start of the timestep
        self.consumptions = consumptions

        self.charge_efficiency = charge_efficiency #This is defined as energy stored / energy imported from grid 
        self.discharge_efficiency = discharge_efficiency #This is defined as energy exported / energy stored
        self.bus = bus
        self.bus.storage_units[self.name] = self  

        # Initialise decision variables
        self.charge_inflows = [] #Always positive
        self.discharge_outflows = [] #Always positive
        self.socs_start_of_ts = []
        self.socs_end_of_ts = []
        for i, ts in enumerate(self.bus.network.timesteps):
            self.charge_inflows.append(LpVariable(f"{self.name}_charge_inflows_{ts}", 0, self.max_charge_capacities[i]))
            self.discharge_outflows.append(LpVariable(f"{self.name}_discharge_outflows_{ts}", 0, self.max_discharge_capacities[i]))
            self.socs_start_of_ts.append(LpVariable(f"{self.name}_soc_start_of_{ts}", 0, self.max_soc_capacity))
            self.socs_end_of_ts.append(LpVariable(f"{self.name}_soc_end_of_{ts}", 0, self.max_soc_capacity))

    
    def __repr__(self):
        return f"{self.name} - Max SOC Capacity: {self.max_soc_capacity} - Max Charge Capacities: {self.max_charge_capacities} - Max Discharge Capacities: {self.max_discharge_capacities}"
    
class EVFleet(StorageUnit):
    """Represents conventional EVs, as well as V2G EVs"""
    def __init__(
        self,
        name: str,
        bus: Bus,
        max_soc_capacity: float,
        max_charge_capacities: list,
        max_discharge_capacities: list,
        min_soc_requirements_start_of_ts: list,
        km_driven: list,
        mwh_per_km_driven: float = 0.3/1000,
        charge_efficiency: float = 0.95,
        discharge_efficiency: float = 0.95,
                    ):
        consumptions = [km * mwh_per_km_driven for km in km_driven]
        super().__init__(
            name,
            bus,
            max_soc_capacity,
            max_charge_capacities,
            max_discharge_capacities,
            min_soc_requirements_start_of_ts,
            consumptions,
            charge_efficiency,
            discharge_efficiency
        )

        
