import folium

CLUSTER_COLORS = [
    "blue", "green", "purple", "orange", "darkred",
    "cadetblue", "darkgreen", "pink", "lightred", "gray"
]

def create_base_map(depot: dict) -> folium.Map:
    m = folium.Map(
        location=[depot["lat"], depot["lon"]],
        zoom_start=13
    )
    folium.Marker(
        location=[depot["lat"], depot["lon"]],
        popup="DEPOT",
        tooltip="📦 Depot",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)
    return m


def plot_customers(m: folium.Map, customers: list, cluster_labels: list) -> folium.Map:
    for i, customer in enumerate(customers):
        cluster_id = cluster_labels[i]
        color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]

        tooltip_text = (
            f"🏠 {customer.get('name', customer['id'])}\n"
            f"📦 Demand: {round(customer.get('demand', 0), 2)} cans\n"
            f"🔵 Cluster: {cluster_id}\n"
            f"📍 ({customer['lat']}, {customer['lon']})"
        )

        popup_html = f"""
        <div style="font-family: Arial; width: 180px;">
            <h4 style="margin:0; color:#333;">
                {customer.get('name', customer['id'])}
            </h4>
            <hr style="margin:4px 0;">
            <b>Customer ID:</b> {customer['id']}<br>
            <b>Demand:</b> {round(customer.get('demand', 0), 2)} cans<br>
            <b>Cluster:</b> {cluster_id}<br>
            <b>Location:</b> {customer['lat']}, {customer['lon']}
        </div>
        """

        folium.CircleMarker(
            location=[customer["lat"], customer["lon"]],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            tooltip=tooltip_text,
            popup=folium.Popup(popup_html, max_width=200)
        ).add_to(m)

    return m


def save_map(m: folium.Map, filename: str = "delivery_map.html"):
    output_path = f"App/static/{filename}"
    m.save(output_path)
    return output_path


def inject_legend(output_path: str, routes: list, driver_assignments: dict):
    legend_rows = ""
    for route_info in routes:
        cluster_id = route_info["cluster_id"]
        color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]

        driver_name = "Unassigned"
        distance = route_info["distance_km"]
        total_demand = round(route_info.get("total_demand", 0), 2)
        num_trips = route_info.get("num_trips", 1)  # ✅ fixed key

        # Count total stops across all trips
        cluster_routes = route_info.get("routes", [])
        if not cluster_routes and "route" in route_info:
            cluster_routes = [{"route": route_info["route"]}]
        total_stops = sum(len(r["route"]) - 2 for r in cluster_routes)

        if driver_assignments:
            for d_id, d_info in driver_assignments.items():
                if isinstance(d_info, dict) and d_info.get("cluster_id") == cluster_id:
                    driver_name = d_id
                    break

        legend_rows += f"""
        <tr>
            <td><div style="width:16px;height:16px;background:{color};
            border-radius:50%;display:inline-block;"></div></td>
            <td style="padding:4px 10px;"><b>Cluster {cluster_id}</b></td>
            <td style="padding:4px 10px;">🚚 {driver_name}</td>
            <td style="padding:4px 10px;">🔁 {num_trips} trip(s)</td>
            <td style="padding:4px 10px;">📦 {total_demand} cans</td>
            <td style="padding:4px 10px;">📏 {distance} km</td>
            <td style="padding:4px 10px;">🛑 {total_stops} stops</td>
        </tr>
        """

    legend_html = f"""
    <div id="map-legend" style="
        position: fixed;
        top: 80px;
        right: 10px;
        z-index: 99999;
        background: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        font-family: Arial, sans-serif;
        font-size: 13px;
        min-width: 480px;
        border: 1px solid #ddd;
    ">
        <h4 style="margin:0 0 10px 0;color:#333;
        border-bottom:2px solid #eee;padding-bottom:6px;">
            🗺️ Delivery Route Legend
        </h4>
        <table style="border-collapse:collapse;width:100%;">
            <tr style="color:#888;font-size:11px;">
                <th></th>
                <th style="padding:2px 10px;text-align:left;">Cluster</th>
                <th style="padding:2px 10px;text-align:left;">Driver</th>
                <th style="padding:2px 10px;text-align:left;">Trips</th>
                <th style="padding:2px 10px;text-align:left;">Demand</th>
                <th style="padding:2px 10px;text-align:left;">Distance</th>
                <th style="padding:2px 10px;text-align:left;">Stops</th>
            </tr>
            {legend_rows}
        </table>
        <hr style="margin:10px 0;border-color:#eee;">
        <div style="display:flex;align-items:center;gap:8px;">
            <div style="width:14px;height:14px;background:red;
            border-radius:50%;display:inline-block;"></div>
            <span>📦 Depot — Starting point for all routes</span>
        </div>
    </div>
    """

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("</body>", legend_html + "</body>")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def plot_routes(m: folium.Map, routes: list, customers: list, depot: dict, driver_assignments: dict = None) -> folium.Map:
    location_map = {"DEPOT": (depot["lat"], depot["lon"])}
    for c in customers:
        location_map[c["id"]] = (c["lat"], c["lon"])

    for cluster_info in routes:
        cluster_id = cluster_info["cluster_id"]
        color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]

        driver_name = "Unassigned"
        total_demand = round(cluster_info.get("total_demand", 0), 2)
        num_trips = cluster_info.get("num_trips", 1)  # ✅ fixed key

        if driver_assignments:
            for d_id, d_info in driver_assignments.items():
                if isinstance(d_info, dict) and d_info.get("cluster_id") == cluster_id:
                    driver_name = d_id
                    break

        cluster_routes = cluster_info.get("routes", [])

        # Fallback for old single route format
        if not cluster_routes and "route" in cluster_info:
            cluster_routes = [{"trip_id": 0, "route": cluster_info["route"]}]

        for i, trip_route in enumerate(cluster_routes):
            trip_id = trip_route.get("trip_id", trip_route.get("vehicle_id", i))  # ✅ support both keys
            route = trip_route["route"]

            points = []
            for stop in route:
                if stop in location_map:
                    points.append(location_map[stop])

            opacity = 0.9 if trip_id == 0 else 0.5

            tooltip_text = (
                f"🚚 Driver: {driver_name} | Trip {trip_id + 1} of {num_trips}\n"
                f"🔵 Cluster: {cluster_id}\n"
                f"📦 Total Demand: {total_demand} cans\n"
                f"📏 Distance: {cluster_info['distance_km']} km\n"
                f"🛣️ Stops this trip: {len(route) - 2}"
            )

            folium.PolyLine(
                locations=points,
                color=color,
                weight=4,
                opacity=opacity,
                tooltip=tooltip_text
            ).add_to(m)

    return m