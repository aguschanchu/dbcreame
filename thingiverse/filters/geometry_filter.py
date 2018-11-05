import copy
import requests
from typing import List, Tuple
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from db.models import Objeto, ArchivoSTL
from ..models import InformacionMesh

def geometry_filter(thing: Objeto, timeout=60):

    #Comprobamos que tengan el atributo de informacion de mesh, y, sino, lo generamos
    for f in thing.files.all():
        if not hasattr(f,'informacionmesh'):
            InformacionMesh.informacion_mesh_de_archivo_stl(f)

    # Create a graph depending of the geometry
    G = create_graph_connections(thing)


    #plot_graph(G)

    reduce_graph(G, thing, timeout)



# noinspection PyUnreachableCode
def create_graph_connections(thing: Objeto, permitted_ratio=0.1) -> nx.Graph:
    G = nx.Graph()

    G = connect_graph_by_mesh(G, [f.informacionmesh for f in thing.files.all()], permitted_ratio)

    # Get sub-graphs
    sub_graphs_list = list(nx.connected_component_subgraphs(G))
    for sub_graph in sub_graphs_list:

        nodes = sub_graph.nodes()

        if len(nodes) == 1:
            continue
        names_list = [(ArchivoSTL.objects.get(pk=id).informacionthingi.original_filename.split('.')[0], id) for id in nodes]

        # Parse sub-graph by keyword
        right_filter = list(filter(lambda x: 'right' in x[0].lower() or x[0].endswith('_R'), names_list))
        left_filter = list(filter(lambda x: 'left' in x[0].lower() or x[0].endswith('_L'), names_list))
        top_filter = list(filter(lambda x: 'top' in x[0].lower(), names_list))
        bottom_filter = list(filter(lambda x: 'bottom' in x[0].lower(), names_list))
        front_filter = list(filter(lambda x: 'front' in x[0].lower(), names_list))
        back_filter = list(filter(lambda x: 'back' in x[0].lower(), names_list))

        if len(right_filter) != 0:
            G = graph_disconnect_ids(G, [id for id in nodes], [item[1] for item in right_filter])
        if len(left_filter) != 0:
            G = graph_disconnect_ids(G, [id for id in nodes], [item[1] for item in left_filter])
        if len(top_filter) != 0:
            G = graph_disconnect_ids(G, [id for id in nodes], [item[1] for item in top_filter])
        if len(bottom_filter) != 0:
            G = graph_disconnect_ids(G, [id for id in nodes], [item[1] for item in bottom_filter])
        if len(front_filter) != 0:
            G = graph_disconnect_ids(G, [id for id in nodes], [item[1] for item in front_filter])
        if len(back_filter) != 0:
            G = graph_disconnect_ids(G, [id for id in nodes], [item[1] for item in back_filter])

    return G


def connect_graph_by_mesh(G: nx.Graph, mesh_data: List[InformacionMesh], permitted_ratio=0.1):

    for i in range(len(mesh_data)):
        if mesh_data[i].volume == 0:    # or (mesh_data[i].is_watertight is False):
            continue
        for j in range(i, len(mesh_data), 1):
            if mesh_data[j].volume == 0:    # or (mesh_data[i].is_watertight is False):
                continue
            if i == j:
                G.add_edge(mesh_data[i].fid, mesh_data[j].fid, weight=1)
            else:
                # Compare bounding box dimensions
                extents_1 = mesh_data[i].bounding_box
                extents_2 = mesh_data[j].bounding_box
                extents_1.sort()
                extents_2.sort()
                extents_1 = np.asfarray(extents_1)
                extents_2 = np.asfarray(extents_2)
                extents_ratio = abs(extents_1 - extents_2) / extents_1 <= permitted_ratio
                ratio_list = list(filter(lambda x: not x, extents_ratio))

                ratio_flag = (len(ratio_list) == 0)

                body_count_flag = (np.abs(mesh_data[i].body_count - mesh_data[j].body_count) <= 1)

                area_flag = (abs(mesh_data[i].area - mesh_data[j].area) / mesh_data[i].area <= permitted_ratio)

                watertight_flag = mesh_data[i].is_watertight and mesh_data[j].is_watertight

                if ratio_flag:
                    if watertight_flag:
                        if body_count_flag and area_flag:
                            G.add_edge(mesh_data[i].fid, mesh_data[j].fid, weight=1)
                    else:
                        G.add_edge(mesh_data[i].fid, mesh_data[j].fid, weight=1)

    return G


def graph_disconnect_ids(G: nx.Graph, cluster_nodes: List[int], disconnect_nodes: List[int]):
    for i in range(len(cluster_nodes)):
        for j in range(len(disconnect_nodes)):
            if cluster_nodes[i] not in disconnect_nodes:
                data = G.get_edge_data(cluster_nodes[i], disconnect_nodes[j])
                if data is not None:
                    G.remove_edge(cluster_nodes[i], disconnect_nodes[j])
    return G


def graph_connect_all(G: nx.Graph, ids_list: List[int]):
    for i in range(len(ids_list)):
        for j in range(i, len(ids_list), 1):
            G.add_edge(ids_list[i], ids_list[j], weight=1)
    return G


def plot_graph(graph):
    elarge = [(u, v) for (u, v, d) in graph.edges(data=True) if d['weight'] > 0.5]
    esmall = [(u, v) for (u, v, d) in graph.edges(data=True) if d['weight'] <= 0.5]
    pos = nx.spring_layout(graph)  # positions for all nodes
    # nodes
    nx.draw_networkx_nodes(graph, pos, node_size=700)
    # edges
    nx.draw_networkx_edges(graph, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(graph, pos, edgelist=esmall, width=6, alpha=0.5, edge_color='b', style='dashed')
    # labels
    nx.draw_networkx_labels(graph, pos, font_size=20, font_family='sans-serif')

    # plt.axis('off')
    plt.show()

'''
Cada subgrafo corresponde a archivos similares. La idea, es quedarnos con un solo archivo ahora 
de cada uno de los subgrafos
'''
def reduce_graph(G, thing, timeout=60):
    # Get sub-graphs
    sub_graphs_list = list(nx.connected_component_subgraphs(G))

    thing_time = 0
    for sub_graph in sub_graphs_list:
        nodes = sub_graph.nodes()
        thing_files: List[ArchivoSTL] = []
        for node in nodes:
            thing_file = ArchivoSTL.objects.get(pk=node)
            thing_files.append(thing_file)
            parsed_thing_file = filter_file_things(thing, thing_files, timeout)
        #Marcamos los otros archivos que no fueron escodigos, como filtrados
        for node in nodes:
            if node != parsed_thing_file.id:
                it = ArchivoSTL.objects.get(pk=node).informacionthingi
                it.filter_passed = False
                it.save()
            else:
                it = ArchivoSTL.objects.get(pk=node).informacionthingi
                it.filter_passed = True
                it.save()



def filter_file_things(thing: Objeto, thing_files: List[ArchivoSTL], timeout=60):
    thing_files.sort(key=lambda x: x.informacionthingi.date, reverse=True)

    pricing = lambda x: x.printing_time_default
    price_list = [pricing(f) for f in thing_files]
    max_price = max(price_list)

    if max_price != 0:      # Este error va a ser corregido por Agus desde la base de datos
        if 0.95 <= price_list[0]/max_price:
            return thing_files[0]
        index = np.argmax(price_list)
        return thing_files[index]

    # Esto lo agrego hasta que Agus corrija el error del tamano de la cama
    fix_list = list(filter(lambda x: 'fix' in x.informacionthingi.original_filename.lower(), thing_files))
    if len(fix_list) == 1:
        return fix_list[0]
    else:
        return thing_files[0]