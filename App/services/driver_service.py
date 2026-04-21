from geopy.distance import geodesic

driver_routes = {}


def get_all_stops(cluster):
    stops = []
    if "routes" in cluster:
        for vehicle_route in cluster["routes"]:
            for stop in vehicle_route["route"]:
                if stop != "DEPOT":
                    stops.append(stop)
    elif "route" in cluster:
        for stop in cluster["route"]:
            if stop != "DEPOT":
                stops.append(stop)
    return stops


def calculate_cluster_demand(cluster, customers):
    if "total_demand" in cluster:
        return cluster["total_demand"]
    total = 0
    for stop in get_all_stops(cluster):
        customer = next((c for c in customers if c["id"] == stop), None)
        if customer:
            total += customer.get("demand", 0)
    return total


def get_vehicle_capacity(driver, vehicles):
    vehicle = next(v for v in vehicles if v["id"] == driver["vehicle_id"])
    return vehicle["capacity"]


def calculate_distance(loc1, loc2):
    return geodesic(loc1, loc2).km


def get_cluster_center(cluster, customers):
    coords = []
    for stop in get_all_stops(cluster):
        customer = next((c for c in customers if c["id"] == stop), None)
        if customer:
            coords.append((customer["lat"], customer["lon"]))
    if not coords:
        return (0, 0)
    avg_lat = sum(c[0] for c in coords) / len(coords)
    avg_lon = sum(c[1] for c in coords) / len(coords)
    return (avg_lat, avg_lon)


# 🔥 FIXED SMART DRIVER ASSIGNMENT
def assign_drivers(clusters, drivers, vehicles, customers, vehicle_capacity_per_trip=100):

    global driver_routes
    driver_routes = {}

    available_drivers = [d for d in drivers if d["status"] == "available"]

    for cluster in clusters:

        cluster_demand = calculate_cluster_demand(cluster, customers)
        cluster_center = get_cluster_center(cluster, customers)
        num_vehicles = cluster.get("num_vehicles", 1)

        best_driver = None
        best_score = float("inf")

        for driver in available_drivers:
            capacity = get_vehicle_capacity(driver, vehicles)

            # ✅ FIXED: driver just needs to handle ONE trip (one vehicle load)
            # OR-Tools already split demand into multiple vehicles
            # So we just check: can this driver's vehicle carry one trip's worth?
            if capacity < vehicle_capacity_per_trip:
                continue

            distance = calculate_distance(driver["location"], cluster_center)

            if distance < best_score:
                best_score = distance
                best_driver = driver

        if best_driver:
            driver_routes[best_driver["id"]] = {
                "cluster_id": cluster["cluster_id"],
                "routes": cluster.get("routes", []),
                "num_vehicles": num_vehicles,
                "total_demand": round(cluster_demand, 2),
                "vehicle_capacity": get_vehicle_capacity(best_driver, vehicles),
                "distance_to_cluster_km": round(best_score, 2)
            }
            available_drivers.remove(best_driver)

        else:
            driver_routes[f"UNASSIGNED_{cluster['cluster_id']}"] = {
                "reason": "No suitable driver — no vehicle meets trip capacity",
                "cluster_id": cluster["cluster_id"],
                "total_demand": cluster_demand,
                "num_vehicles_needed": num_vehicles
            }

    return driver_routes