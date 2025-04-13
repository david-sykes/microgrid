import unittest
from engine import Network, Bus, Generator, Load, TransmissionLine, StorageUnit, EVFleet  # replace with your actual module name
from draw import draw_network
from save import save_network
import os

output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../test_outputs/")

def save_network_outputs(n):
    os.makedirs(os.path.join(output_dir, n.name.replace(' ', '-')), exist_ok=True)
    save_network(n, os.path.join(output_dir,n.name.replace(' ', '-'), f"{n.name.replace(' ', '-')}.json"))

    for ts in n.timesteps:
        dot = draw_network(n, ts)
        dot.render(os.path.join(output_dir,n.name.replace(' ', '-'), f"{n.name.replace(' ', '-')}_{ts}"), format='png')

class OptimalDispatchSingleNode(unittest.TestCase):

    def test_network(self):
        timesteps = ['t0', 't1']
        n = Network("Simple1Node", timesteps)

        bus = Bus("Bus1", n)
        Generator("Gen1", capacities=[10, 10], costs=[5, 10], bus=bus)
        Generator("Gen2", capacities=[10, 10], costs=[7, 7], bus=bus)

        Load("Load1", consumptions=[9, 9], bus=bus)

        status = n.solve()
        
        save_network_outputs(n)

        self.assertEqual(status, "Optimal")
        self.assertAlmostEqual(bus.generators["Gen1"].outputs[0].varValue, 9.0)
        self.assertAlmostEqual(bus.generators["Gen1"].outputs[1].varValue, 0.0)
        self.assertAlmostEqual(bus.generators["Gen2"].outputs[0].varValue, 0.0)
        self.assertAlmostEqual(bus.generators["Gen2"].outputs[1].varValue, 9.0)
        self.assertAlmostEqual(bus.nodal_prices[0], 5.0)
        self.assertAlmostEqual(bus.nodal_prices[1], 7.0)

class NodalPriceNetwork(unittest.TestCase):

    def test_network(self):
        timesteps = ['t0', 't1']
        n = Network("Simple2Node", timesteps)

        bus1 = Bus("Bus1", n)
        Generator("Gen1", capacities=[10, 15], costs=[0, 0], bus=bus1)
        Load("Load1", consumptions=[10, 10], bus=bus1)

        bus2 = Bus("Bus2", n)
        Generator("Gen2", capacities=[10, 5], costs=[5, 5], bus=bus2)
        Load("Load2", consumptions=[10, 10], bus=bus2)

        t = TransmissionLine(start_bus=bus1, end_bus=bus2, capacities=[5, 5], network=n)

        status = n.solve()
        save_network_outputs(n)

        self.assertEqual(status, "Optimal")
        self.assertAlmostEqual(n.buses["Bus1"].nodal_prices[0], 5.0)
        self.assertAlmostEqual(n.buses["Bus1"].nodal_prices[1], 0.0)
        self.assertAlmostEqual(n.buses["Bus2"].nodal_prices[0], 5.0)
        self.assertAlmostEqual(n.buses["Bus2"].nodal_prices[1], 5.0)

class BatteryStorage(unittest.TestCase):

    def test_network(self):
        timesteps = ['t0', 't1', 't3']
        n = Network("SimpleStorage", timesteps)

        bus1 = Bus("Bus1", n)
        Generator("Gen1", capacities=[30, 30, 30], costs=[5, 100, 100], bus=bus1)
        Load("Load1", consumptions=[10, 10, 10], bus=bus1)
        StorageUnit("Storage1", bus=bus1, max_soc_capacity=100, max_charge_capacities=[20, 20, 20], 
                    max_discharge_capacities=[10, 10, 10], min_soc_requirements_start_of_ts=[0, 0, 0], consumptions=[0, 0, 0],
                    charge_efficiency=1, discharge_efficiency=1)
                    

        status = n.solve()
        save_network_outputs(n)

        self.assertEqual(status, "Optimal")
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[0].varValue, 30.0)
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[1].varValue, 0.0)
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[2].varValue, 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].charge_inflows[0].varValue, 20.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].charge_inflows[1].varValue, 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].charge_inflows[2].varValue, 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].discharge_outflows[0].varValue, 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].discharge_outflows[1].varValue, 10.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].discharge_outflows[2].varValue, 10.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_start_of_ts[0], 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_start_of_ts[1], 20.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_start_of_ts[2], 10.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_end_of_ts[0], 20.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_end_of_ts[1], 10.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_end_of_ts[2], 0.0)


class BatteryStorage(unittest.TestCase):

    def test_network(self):
        timesteps = ['t0', 't1', 't3']
        n = Network("SimpleStorage", timesteps)

        bus1 = Bus("Bus1", n)
        Generator("Gen1", capacities=[30, 30, 30], costs=[5, 100, 100], bus=bus1)
        Load("Load1", consumptions=[10, 10, 10], bus=bus1)
        StorageUnit("Storage1", bus=bus1, max_soc_capacity=100, max_charge_capacities=[20, 20, 20], 
                    max_discharge_capacities=[10, 10, 10], min_soc_requirements_start_of_ts=[0, 0, 0], consumptions=[0, 0, 0],
                    charge_efficiency=1, discharge_efficiency=1)

        status = n.solve()
        save_network_outputs(n)

        self.assertEqual(status, "Optimal")
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[0].varValue, 30.0)
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[1].varValue, 0.0)
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[2].varValue, 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].charge_inflows[0].varValue, 20.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].charge_inflows[1].varValue, 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].charge_inflows[2].varValue, 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].discharge_outflows[0].varValue, 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].discharge_outflows[1].varValue, 10.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].discharge_outflows[2].varValue, 10.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_start_of_ts[0], 0.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_start_of_ts[1], 20.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_start_of_ts[2], 10.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_end_of_ts[0], 20.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_end_of_ts[1], 10.0)
        self.assertAlmostEqual(bus1.storage_units["Storage1"].socs_end_of_ts[2], 0.0)


class EVFleetNetwork(unittest.TestCase):

    def test_network(self):
        timesteps = ['t0', 't1', 't3', 't4']
        n = Network("EVFleet", timesteps)

        bus1 = Bus("Bus1", n)
        Generator("Gen1", capacities=[30, 30, 30, 30], costs=[20, 10, 20, 20], bus=bus1)
        EVFleet("EVFleet", bus=bus1, max_soc_capacity=10, max_charge_capacities=[20, 20, 20, 20], 
                    max_discharge_capacities=[0, 0, 0, 0], min_soc_requirements_start_of_ts=[0, 0, 0, 0],
                    charge_efficiency=1, discharge_efficiency=1, km_driven=[0, 0, 33_333, 0], mwh_per_km_driven=0.3/1000)

        status = n.solve()
        save_network_outputs(n)

        self.assertEqual(status, "Optimal")
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[0].varValue, 0.0)
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[1].varValue, 10.0, delta=0.01)
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[2].varValue, 0.0, delta=0.01)
        self.assertAlmostEqual(bus1.generators["Gen1"].outputs[3].varValue, 0.0, delta=0.01)

        self.assertAlmostEqual(bus1.storage_units["EVFleet"].consumptions[0], 0.0, delta=0.01)
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].consumptions[1], 0.0, delta=0.01)
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].consumptions[2], 10.0, delta=0.01)
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].consumptions[3], 0.0, delta=0.01)

        self.assertAlmostEqual(bus1.storage_units["EVFleet"].charge_inflows[0].varValue, 0.0, delta=0.01)
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].charge_inflows[1].varValue, 10.0, delta=0.01)
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].charge_inflows[2].varValue, 0.0, delta=0.01)
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].charge_inflows[3].varValue, 0.0, delta=0.01)

        self.assertAlmostEqual(bus1.storage_units["EVFleet"].socs_end_of_ts[0].varValue, 0.0, delta=0.01)        
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].socs_end_of_ts[1].varValue, 10.0, delta=0.01)        
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].socs_end_of_ts[2].varValue, 0.0, delta=0.01)        
        self.assertAlmostEqual(bus1.storage_units["EVFleet"].socs_end_of_ts[3].varValue, 0.0, delta=0.01)        

class AllElements(unittest.TestCase):

    def test_network(self):
        timesteps = ['t0', 't1', 't3', 't4']
        n = Network("AllElements", timesteps)

        bus1 = Bus("Bus1", n)
        Generator("Wind", capacities=[100, 15, 0, 0], costs=[0, 0, 0, 0], bus=bus1)
        Load("Load1", consumptions=[15, 15, 10, 15], bus=bus1)
        StorageUnit("Storage1", bus=bus1, max_soc_capacity=10, max_charge_capacities=[5, 5, 5, 5], 
                    max_discharge_capacities=[5, 5, 5, 5], min_soc_requirements_start_of_ts=[0, 0, 0, 0], consumptions=[0, 0, 0, 0],
                    charge_efficiency=1, discharge_efficiency=1)

        bus2 = Bus("Bus2", n)
        Generator("Gas", capacities=[15, 15, 15, 15], costs=[5, 5, 5, 5], bus=bus2)
        Load("Load2", consumptions=[10, 10, 10, 10], bus=bus2)

        t = TransmissionLine(start_bus=bus1, end_bus=bus2, capacities=[10, 10, 10, 10], network=n)

        status = n.solve()
        save_network_outputs(n)

        self.assertEqual(status, "Optimal")



if __name__ == "__main__":
    unittest.main()
