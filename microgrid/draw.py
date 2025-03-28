from graphviz import Digraph


def draw_network(network, timestep):
    timestep_index = network.timestep_index[timestep]
    dot = Digraph(comment='Energy Network')
    dot.graph_attr['rankdir'] = 'LR'
    for b in network.buses:
        total_demand = sum([l.demands[timestep_index] for l in b.loads]) 
        dot.node(b.name, label=f"{b.name}: {total_demand} MW \n {b.nodal_prices[timestep_index]} £/MWh", shape='doubleoctagon')
        for g in b.generators:
            dot.node(g.name, label=f"{g.name}: £{g.costs[timestep_index]}/MWh")
            dot.edge(g.name, b.name, label=f"{g.outputs[timestep_index].varValue} / {g.capacities[timestep_index]}")
        for l in b.loads:
            dot.node(l.name, label=f"{l.name}: {l.demands[timestep_index]}MW", shape='house')
            dot.edge(b.name, l.name)
        for su in b.storage_units:
            dot.node(su.name, label=f"""{su.name}\nStart SOC: {su.socs_start_of_ts[timestep_index].varValue} / {su.max_soc_capacity}\nEnd SOC: {su.socs_end_of_ts[timestep_index].varValue} / {su.max_soc_capacity}""", shape='cylinder')
            if su.net_inflows[timestep_index].varValue > 0:
                dot.edge(b.name, su.name, label=f"{su.net_inflows[timestep_index].varValue} / {su.max_charge_capacities[timestep_index]}")
            elif su.net_inflows[timestep_index].varValue < 0:
                dot.edge(su.name, b.name, label=f"{-su.net_inflows[timestep_index].varValue} / {su.max_discharge_capacities[timestep_index]}")
            elif su.net_inflows[timestep_index].varValue == 0:
                dot.edge(b.name, su.name, label=f"{su.net_inflows[timestep_index].varValue} / {su.max_charge_capacities[timestep_index]}",
                arrowhead='none')
    for t in network.transmission_lines.values():
        if t.flows[timestep_index].varValue > 0:
            dot.edge(t.start_bus.name, t.end_bus.name,
                    label=f"{t.flows[timestep_index].varValue} / {t.capacities[timestep_index]}", color='blue', fontcolor='blue')
        else:
            dot.edge(t.end_bus.name, t.start_bus.name,
                    label=str(-t.flows[timestep_index].varValue), color='blue', fontcolor='blue')
    return dot