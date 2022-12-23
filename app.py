import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon, LineString, mapping
from descartes import PolygonPatch
import os
import fiona

def main(network_type: str, trip_times: list, point:tuple, dist:int, travel_speed=4.5) :
    network_type = network_type
    trip_times = trip_times #in minutes
    travel_speed = travel_speed #walking speed in km/hour
    point = point
    dist = dist #meter
    
    G = ox.graph_from_point(point, network_type=network_type, dist=dist, simplify=False)
    gdf_nodes = ox.graph_to_gdfs(G, edges=False)
    x, y = gdf_nodes['geometry'].unary_union.centroid.xy
    center_node = ox.distance.nearest_nodes(G, Y=point[0], X=point[1])
    G = ox.project_graph(G)
    
    meters_per_minute = travel_speed * 1000 / 60 #km per hour to m per minute
    for u, v, k, data in G.edges(data=True, keys=True):
        data['time'] = data['length'] / meters_per_minute

    isochrone_polys = []
    timezone_polys = []
    for trip_time in sorted(trip_times, reverse=True):
        subgraph = nx.ego_graph(G,
                                center_node,
                                radius=trip_time,
                                distance='time')
        node_points = [Point((data['x'], data['y'])) for node, data in subgraph.nodes(data=True)]
        make_points = [Point((data['lon'], data['lat'])) for node, data in subgraph.nodes(data=True)]
        bounding_poly = gpd.GeoSeries(node_points).unary_union.convex_hull
        make_poly = gpd.GeoSeries(make_points).unary_union.convex_hull
        isochrone_polys.append(bounding_poly)
        timezone_polys.append(make_poly)

    os.makedirs('./result', exist_ok=True)
    for index, times in enumerate(sorted(trip_times, reverse=True)) :
        schema = {
            'geometry': 'Polygon',
            'properties': {'id': 'int'},
        }

        with fiona.open(f'./result/timezone_{times}.shp', 'w',
                        'ESRI Shapefile',
                        crs='epsg:4326',
                        schema=schema) as c:
            c.write({
                'geometry': mapping(timezone_polys[index]),
                'properties': {'id': int(times)},
            })

        gpd.read_file(f'./result/timezone_{times}.shp').to_crs('epsg:5179').to_file(f'./result/timezone_{times}.shp')

if __name__=='__main__' :
    main(
        network_type='walk',
        trip_times=[5,10,15,20],
        point=(37.660246, 127.120493),
        dist=1500)