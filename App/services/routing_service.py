import math
from geopy.distance import geodesic
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sklearn.cluster import KMeans


def optimize_routes(data):
    depot = (data["depot"]["lat"], data["depot"]["lon"])
    customers = data["customers"]
    num_clusters = data["num_clusters"]
    vehicle_capacity = data["vehicle_capacity"]

    # STEP 1: Clustering
    coords = [(c["lat"], c["lon"]) for c in customers]
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    labels = kmeans.fit_predict(coords)

    for i, c in enumerate(customers):
        c["cluster"] = int(labels[i])

    results = []

    # STEP 2: Solve each cluster
    for cluster_id in range(num_clusters):
        cluster_customers = [c for c in customers if c["cluster"] == cluster_id]

        if not cluster_customers:
            continue

        total_demand = sum(c.get("demand", c.get("predicted_demand", 0)) for c in cluster_customers)

        # num_trips = how many trips 1 driver needs to complete this cluster
        num_trips = max(1, math.ceil(total_demand / vehicle_capacity))

        routes, distance = solve_cluster(depot, cluster_customers, vehicle_capacity, num_trips)

        results.append({
            "cluster_id": cluster_id,
            "num_trips": num_trips,              # ✅ renamed from num_vehicles
            "total_demand": round(total_demand, 2),
            "vehicle_capacity": vehicle_capacity,
            "routes": routes,
            "distance_km": distance
        })

    return {"clusters": results}


def solve_cluster(depot, cluster_customers, vehicle_capacity, num_trips):
    nodes = [depot] + [(c["lat"], c["lon"]) for c in cluster_customers]
    id_map = ["DEPOT"] + [c["id"] for c in cluster_customers]

    demands = [0] + [
        int(round(c.get("demand", c.get("predicted_demand", 0))))
        for c in cluster_customers
    ]

    dist_matrix = [
        [geodesic(a, b).km for b in nodes]
        for a in nodes
    ]

    # OR-Tools setup — num_trips used as vehicle count internally
    manager = pywrapcp.RoutingIndexManager(len(nodes), num_trips, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_idx, to_idx):
        from_node = manager.IndexToNode(from_idx)
        to_node = manager.IndexToNode(to_idx)
        return int(dist_matrix[from_node][to_node] * 1000)

    transit_cb = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    def demand_callback(from_idx):
        from_node = manager.IndexToNode(from_idx)
        return demands[from_node]

    demand_cb = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_cb,
        0,
        [vehicle_capacity] * num_trips,
        True,
        "Capacity"
    )

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(search_params)

    if not solution:
        return [], 0

    all_routes = []
    total_distance = 0

    for trip_id in range(num_trips):
        index = routing.Start(trip_id)
        route = []

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route.append(id_map[node])
            prev_index = index
            index = solution.Value(routing.NextVar(index))
            total_distance += routing.GetArcCostForVehicle(prev_index, index, trip_id)

        route.append("DEPOT")

        # Only include trips that actually visit customers
        if len(route) > 2:
            all_routes.append({
                "trip_id": trip_id,          # ✅ renamed from vehicle_id
                "route": route
            })

    return all_routes, total_distance / 1000