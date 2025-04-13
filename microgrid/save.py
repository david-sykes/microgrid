import json

def unpack_lp_var_list(var_list):
    return [v.varValue for v in var_list]

def save_network(n, output_path):
    network_output = {'network': {
        'name': n.name,
        'timesteps': n.timesteps,
        'buses': {
            bus.name: {
                'generators': {
                    gen.name: {
                        'capacity': gen.capacities,
                        'cost': gen.costs,
                        'output': unpack_lp_var_list(gen.outputs)
                    }
                    for gen in bus.generators.values()
                },
                'loads': {
                    load.name: {
                        'consumption': load.consumptions
                    }
                    for load in bus.loads.values()
                },
                'storage_units': {
                    su.name: {
                        'max_soc_capacity': su.max_soc_capacity,
                        'max_charge_capacity': su.max_charge_capacities,
                        'max_discharge_capacity': su.max_discharge_capacities,
                        'min_soc_requirements': su.min_soc_requirements_start_of_ts,
                        'consumption': su.consumptions,
                        'charge_inflows': unpack_lp_var_list(su.charge_inflows),
                        'discharge_outflows': unpack_lp_var_list(su.discharge_outflows),
                        'soc_start_of_ts':unpack_lp_var_list(su.socs_start_of_ts),
                        'soc_end_of_ts': unpack_lp_var_list(su.socs_end_of_ts)
                    }
                    for su in bus.storage_units.values()
                }
            }
            for bus in n.buses.values()
        },
        'transmission_lines': {
            line.name: {
                'capacity': line.capacities,
                'flow': unpack_lp_var_list(line.flows)
            }
            for line in n.transmission_lines.values()
        }
    }}

    with open(output_path, 'w') as f:
        json.dump(network_output, f, indent=4)