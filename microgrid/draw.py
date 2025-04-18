from graphviz import Digraph


def draw_network(network, timestep):
    timestep_index = network.timestep_index[timestep]
    dot = Digraph(comment='Energy Network')
    dot.graph_attr['rankdir'] = 'LR'
    for b in network.buses.values():
        total_consumption = sum([l.consumptions[timestep_index] for l in b.loads.values()]) 
        dot.node(b.name, label=f"{b.name}: {total_consumption: .0f} MW \n {b.nodal_prices[timestep_index]} £/MWh", shape='doubleoctagon')
        # Generators
        for g in b.generators.values():
            dot.node(g.name, label=f"{g.name}: £{g.costs[timestep_index]}/MWh")
            dot.edge(g.name, b.name, label=f"{g.outputs[timestep_index].varValue: .0f} / {g.capacities[timestep_index]}")

        # Loads
        for l in b.loads.values():
            dot.node(l.name, label=f"{l.name}: {l.consumptions[timestep_index]: .0f}MW", shape='house')
            dot.edge(b.name, l.name)

        # Storage
        for su in b.storage_units.values():
            dot.node(su.name, label=f"""{su.name}\nStart SOC: {su.socs_start_of_ts[timestep_index].varValue: .0f} / {su.max_soc_capacity}\nEnd SOC: {su.socs_end_of_ts[timestep_index].varValue: .0f} / {su.max_soc_capacity}\nMWh consumed: {su.consumptions[timestep_index]: .0f}""", shape='cylinder')
            dot.edge(b.name, su.name, label=f"{su.charge_inflows[timestep_index].varValue: .0f} / {su.max_charge_capacities[timestep_index]}")
            dot.edge(su.name, b.name, label=f"{su.discharge_outflows[timestep_index].varValue: .0f} / {su.max_discharge_capacities[timestep_index]}")

    # Transmission Lines          
    for t in network.transmission_lines.values():
        if t.flows[timestep_index].varValue > 0:
            dot.edge(t.start_bus.name, t.end_bus.name,
                    label=f"{t.flows[timestep_index].varValue: .0f} / {t.capacities[timestep_index]}", color='blue', fontcolor='blue')
        else:
            dot.edge(t.end_bus.name, t.start_bus.name,
                    label=f"{-t.flows[timestep_index].varValue: .0f}", color='blue', fontcolor='blue')
    return dot