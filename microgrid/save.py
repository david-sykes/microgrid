import json
import duckdb
import os
import pandas as pd
import numpy as np

def unpack_lp_var_list(var_list):
    return [v.varValue for v in var_list]

def save_network_json(n, output_path):
    network_output = {'network': {
        'name': n.name,
        'timesteps': [(i, ts) for i, ts in enumerate(n.timesteps)],
        'buses': {
            bus.name: {
                'generators': {
                    gen.name: {
                        'capacities': gen.capacities,
                        'costs': gen.costs,
                        'outputs': unpack_lp_var_list(gen.outputs),
                        'generator_type': gen.generator_type.value if gen.generator_type else None,
                    }
                    for gen in bus.generators.values()
                },
                'loads': {
                    load.name: {
                        'consumptions': load.consumptions
                    }
                    for load in bus.loads.values()
                },
                'storage_units': {
                    su.name: {
                        'max_soc_capacity': su.max_soc_capacity,
                        'max_charge_capacities': su.max_charge_capacities,
                        'max_discharge_capacities': su.max_discharge_capacities,
                        'min_soc_requirements': su.min_soc_requirements_start_of_ts,
                        'consumptions': su.consumptions,
                        'charge_inflows': unpack_lp_var_list(su.charge_inflows),
                        'discharge_outflows': unpack_lp_var_list(su.discharge_outflows),
                        'soc_start_of_ts':unpack_lp_var_list(su.socs_start_of_ts),
                        'soc_end_of_ts': unpack_lp_var_list(su.socs_end_of_ts),
                        'storage_type': su.storage_type.value if su.storage_type else None,
                        
                    }
                    for su in bus.storage_units.values()
                },
                'nodal_prices': bus.nodal_prices
            }
            for bus in n.buses.values()
        },
        'transmission_lines': {
            line.name: {
                'capacities': line.capacities,
                'flows': unpack_lp_var_list(line.flows),
                'start_bus': line.start_bus.name,
                'end_bus': line.end_bus.name
            }
            for line in n.transmission_lines.values()
        }
    }}

    with open(output_path, 'w') as f:
        json.dump(network_output, f, indent=4)

def save_network_duckdb(n, output_path):

    # Test if timesteps is list of tuples if so unpack and join with '-'
    if isinstance(n.timesteps[0], tuple) or isinstance(n.timesteps[0], list):
        timesteps = [f"{ts[0]}_{ts[1]}" for ts in n.timesteps]
    else:
        timesteps = n.timesteps


    bus_prices = []

    ## Write Nodal prices
    for bus_name, bus in n.buses.items():
        nodal_prices = bus.nodal_prices
        price_series = pd.Series(nodal_prices, name=f'price_{bus_name.replace(' ', '-')}')
        bus_prices.append(price_series)
    
    price_df = pd.concat(bus_prices, axis=1)
    
    price_df['timestep'] = timesteps
    
    with duckdb.connect(output_path) as conn:
        # Nodal prices
        conn.sql("DROP TABLE IF EXISTS nodal_prices")
        conn.sql("CREATE TABLE nodal_prices AS SELECT * FROM price_df")


    # Write generator outputs
    generator_outputs = []

    for bus_name, bus in n.buses.items():
        for generator_name, generator in bus.generators.items():
            generator_df = pd.DataFrame(
                data={
                    'output': [o.varValue for o in generator.outputs],
                    'timestep': timesteps
                }
            )
            generator_df['bus'] = bus_name
            generator_df['generator'] = generator_name
            generator_df['generator_type'] = generator.generator_type.value if generator.generator_type else 'Unclassified'
            generator_outputs.append(generator_df)

    if generator_outputs:
        generator_outputs_df = pd.concat(generator_outputs, axis=0)
        with duckdb.connect(output_path) as conn:
            # Generator outputs
            conn.sql("DROP TABLE IF EXISTS generator_outputs")
            conn.sql("CREATE TABLE generator_outputs AS SELECT * FROM generator_outputs_df")

    
    # Write storage unit inputs outputs and SOC
    
    storage_unit_outputs = []
    
    for bus_name, bus in n.buses.items():
        for storage_unit_name, storage_unit in bus.storage_units.items():
            storage_unit_df = pd.DataFrame(
                data={
                    'charge_inflow': [o.varValue for o in storage_unit.charge_inflows],
                    'discharge_outflow': [o.varValue for o in storage_unit.discharge_outflows],
                    'soc_start_of_ts': [o.varValue for o in storage_unit.socs_start_of_ts],
                    'soc_end_of_ts': [o.varValue for o in storage_unit.socs_end_of_ts],
                    'consumptions': storage_unit.consumptions,
                    'timestep': timesteps
                }
            )
            storage_unit_df['bus'] = bus_name
            storage_unit_df['storage_unit'] = storage_unit_name
            storage_unit_df['storage_type'] = storage_unit.storage_type.value if storage_unit.storage_type else 'Unclassified'
            storage_unit_outputs.append(storage_unit_df)

    if storage_unit_outputs:
        storage_unit_outputs_df = pd.concat(storage_unit_outputs, axis=0)
        with duckdb.connect(output_path) as conn:
            # Storage unit outputs
            conn.sql("DROP TABLE IF EXISTS storage_unit_outputs")
            conn.sql("CREATE TABLE storage_unit_outputs AS SELECT * FROM storage_unit_outputs_df")


    # Nodal flows by bus
    nodal_flows = []
    for bus_name, bus in n.buses.items():
        for generator in bus.generators.values():
            flow = pd.DataFrame(
                data = {
                    'flow_in_amount': [max(o.varValue, 0) for o in generator.outputs],
                    'flow_out_amount': [- min(o.varValue, 0) for o in generator.outputs],
                }
                )
            flow['flow_type'] = 'generator'
            flow['item_name'] = generator.name
            flow['subtype'] = generator.generator_type.value if generator.generator_type else 'Unclassified'
            flow['bus'] = bus_name
            flow['timestep'] = timesteps
            flow['net_flow'] = flow['flow_in_amount'] - flow['flow_out_amount']
            nodal_flows.append(flow)
        
        for storage_unit in bus.storage_units.values():
            flow = pd.DataFrame(
                data = {
                    'flow_in_amount': [o.varValue for o in storage_unit.discharge_outflows],
                    'flow_out_amount': [o.varValue for o in storage_unit.charge_inflows],
                }
                )
            flow['flow_type'] = 'storage_unit'
            flow['item_name'] = storage_unit.name
            flow['subtype'] = storage_unit.storage_type.value if storage_unit.storage_type else 'Unclassified'
            flow['bus'] = bus_name
            flow['timestep'] = timesteps
            flow['net_flow'] = flow['flow_in_amount'] - flow['flow_out_amount']
            nodal_flows.append(flow)

        for load_name, load in bus.loads.items():
            flow = pd.DataFrame(
                data = {
                    'flow_out_amount': [max(o, 0) for o in load.consumptions],
                    'flow_in_amount': [- min(o,0) for o in load.consumptions],
                }
                )
            flow['flow_type'] = 'load'
            flow['item_name'] = load_name
            flow['bus'] = bus_name
            flow['timestep'] = timesteps
            flow['net_flow'] = flow['flow_in_amount'] - flow['flow_out_amount']
            nodal_flows.append(flow)

    for transmission_line_name, transmission_line in n.transmission_lines.items():
        start_bus = transmission_line.start_bus.name
        end_bus = transmission_line.end_bus.name

    # The tranmission line flow is recorded twice in the table, once for the start bus and once for the end bus
        start_bus_flow = pd.DataFrame(
            data = {
                'flow_out_amount': [max(o.varValue, 0) for o in transmission_line.flows],
                'flow_in_amount': [- min(o.varValue, 0) for o in transmission_line.flows],
                'timestep': timesteps
            }
            )
        start_bus_flow['flow_type'] = 'transmission_line'
        start_bus_flow['item_name'] = transmission_line_name
        start_bus_flow['subtype'] = 'transmission_line'
        start_bus_flow['bus'] = start_bus
        start_bus_flow['net_flow'] = start_bus_flow['flow_in_amount'] - start_bus_flow['flow_out_amount']

        nodal_flows.append(start_bus_flow)

        
        end_bus_flow = pd.DataFrame(
            data = {
                'flow_in_amount': [max(o.varValue, 0) for o in transmission_line.flows],
                'flow_out_amount': [- min(o.varValue,0) for o in transmission_line.flows],
                'timestep': timesteps
            }
        )
        end_bus_flow['flow_type'] = 'transmission_line'
        end_bus_flow['item_name'] =  transmission_line_name
        end_bus_flow['subtype'] = 'transmission_line'
        end_bus_flow['bus'] = end_bus
        end_bus_flow['net_flow'] = end_bus_flow['flow_in_amount'] - end_bus_flow['flow_out_amount']

        nodal_flows.append(end_bus_flow)

    if nodal_flows:
        nodal_flows_df = pd.concat(nodal_flows, axis=0)
        with duckdb.connect(output_path) as conn:
            # Nodal flows
            conn.sql("DROP TABLE IF EXISTS nodal_flows")
            conn.sql("CREATE TABLE nodal_flows AS SELECT * FROM nodal_flows_df")
 




    



        
def save_network(n, json_output_path, duckdb_output_path):
    save_network_json(n, json_output_path)
    save_network_duckdb(n, duckdb_output_path)


