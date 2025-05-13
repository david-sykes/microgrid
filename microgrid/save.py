import json

def unpack_lp_var_list(var_list):
    return [v.varValue for v in var_list]

def save_network(n, output_path):
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