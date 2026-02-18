import math
from typing import List, Tuple, Dict
from functools import lru_cache

# Параметры кластеризации
CLUSTER_RADIUS_KM = 3.0   # точки в пределах 3 км друг от друга = один кластер
DISTANT_THRESHOLD_KM = 8.0  # точка > 8 км от кластера = отдельная

# Haversine formula to calculate distance between two lat/lon points
# Кешируем результаты для часто используемых координат
@lru_cache(maxsize=1000)
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Вычисляет расстояние между двумя точками на Земле по формуле Haversine.
    Результаты кешируются для оптимизации.
    """
    R = 6371  # Earth radius in kilometers

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def _optimize_route_sync(current_location: Tuple[float, float], orders_data: List[Dict]) -> Tuple[List[Dict], float]:
    """
    Nearest Neighbor алгоритм для оптимизации маршрута.
    orders_data items must have 'lat', 'lon' keys.
    Returns (sorted_orders, total_distance_km).
    """
    unvisited = orders_data[:]
    visited = []
    total_dist = 0.0
    current_lat, current_lon = current_location

    while unvisited:
        nearest_order = None
        min_dist = float('inf')
        for order in unvisited:
            dist = haversine_distance(current_lat, current_lon, order['lat'], order['lon'])
            if dist < min_dist:
                min_dist = dist
                nearest_order = order
        visited.append(nearest_order)
        unvisited.remove(nearest_order)
        total_dist += min_dist
        current_lat = nearest_order['lat']
        current_lon = nearest_order['lon']
    return visited, total_dist


async def optimize_route(current_location: Tuple[float, float], orders_data: List[Dict]) -> Tuple[List[Dict], float]:
    """Async-обёртка над _optimize_route_sync (для обратной совместимости)."""
    return _optimize_route_sync(current_location, orders_data)


def build_clusters(orders_data: List[Dict], max_dist_km: float) -> List[List[Dict]]:
    """
    Кластеризация точек методом Union-Find.
    Точки в пределах max_dist_km друг от друга объединяются в один кластер.
    """
    n = len(orders_data)
    parent = list(range(n))

    def find(x: int) -> int:
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            dist = haversine_distance(
                orders_data[i]['lat'], orders_data[i]['lon'],
                orders_data[j]['lat'], orders_data[j]['lon']
            )
            if dist <= max_dist_km:
                union(i, j)

    clusters_dict: Dict[int, List[Dict]] = {}
    for i in range(n):
        root = find(i)
        if root not in clusters_dict:
            clusters_dict[root] = []
        clusters_dict[root].append(orders_data[i])

    return list(clusters_dict.values())


def _cluster_centroid(cluster: List[Dict]) -> Tuple[float, float]:
    """Центроид кластера (средние координаты)."""
    if not cluster:
        return 0.0, 0.0
    lat_sum = sum(o['lat'] for o in cluster)
    lon_sum = sum(o['lon'] for o in cluster)
    return lat_sum / len(cluster), lon_sum / len(cluster)


def _min_dist_to_clusters(point: Dict, clusters: List[List[Dict]], exclude_cluster_idx: int = -1) -> float:
    """Минимальное расстояние от точки до любого кластера (кроме exclude_cluster_idx)."""
    min_d = float('inf')
    for idx, cluster in enumerate(clusters):
        if idx == exclude_cluster_idx:
            continue
        for o in cluster:
            d = haversine_distance(point['lat'], point['lon'], o['lat'], o['lon'])
            min_d = min(min_d, d)
    return min_d


async def optimize_route_with_clusters(
    current_location: Tuple[float, float],
    orders_data: List[Dict],
    cluster_radius_km: float = CLUSTER_RADIUS_KM,
    distant_threshold_km: float = DISTANT_THRESHOLD_KM,
) -> Tuple[List[Dict], List[Dict], float]:
    """
    Разделяет заказы на групповой маршрут (близкие точки) и отдельные (вдали 8+ км).
    Returns: (grouped_route, distant_orders, total_grouped_distance_km)
    """
    if not orders_data:
        return [], [], 0.0

    clusters = build_clusters(orders_data, cluster_radius_km)

    grouped_clusters: List[List[Dict]] = []
    distant_orders: List[Dict] = []

    for idx, cluster in enumerate(clusters):
        if len(cluster) == 1:
            point = cluster[0]
            min_d = _min_dist_to_clusters(point, clusters, exclude_cluster_idx=idx)
            if min_d >= distant_threshold_km:
                distant_orders.append(point)
            else:
                grouped_clusters.append(cluster)
        else:
            grouped_clusters.append(cluster)

    grouped_route: List[Dict] = []
    total_dist = 0.0
    curr_lat, curr_lon = current_location

    if grouped_clusters:
        sorted_clusters = sorted(
            grouped_clusters,
            key=lambda c: haversine_distance(curr_lat, curr_lon, *_cluster_centroid(c))
        )

        for cluster in sorted_clusters:
            ordered, seg_dist = _optimize_route_sync((curr_lat, curr_lon), cluster)
            grouped_route.extend(ordered)
            total_dist += seg_dist
            curr_lat, curr_lon = ordered[-1]['lat'], ordered[-1]['lon']

    distant_orders_sorted = sorted(
        distant_orders,
        key=lambda o: haversine_distance(current_location[0], current_location[1], o['lat'], o['lon'])
    )

    return grouped_route, distant_orders_sorted, total_dist


def generate_yandex_maps_url(orders: List[Dict]) -> str:
    """
    Generates a Yandex Maps URL with multiple waypoints.
    Format: yandexmaps://maps.yandex.ru/?rtext=lat1,lon1~lat2,lon2...
    Or web: https://yandex.ru/maps/?rtext=lat1,lon1~lat2,lon2...
    """
    if not orders:
        return ""
    
    # rtext format: start_lat,start_lon~waypoint1~waypoint2...
    # We should probably start from current location, but often users just want the route between points.
    # The prompt implies the courier is at "current location", so the route starts THERE.
    # But for the URL, we usually pass the *destination* points. 
    # If we want the nav to build path FROM CURSOR, we can omit the first point or include the first order.
    # Let's concatenate all destination points.
    
    waypoints = [f"{o['lat']},{o['lon']}" for o in orders]
    route_str = "~".join(waypoints)
    # ~ в начале — маршрут от текущей геолокации пользователя
    return f"https://yandex.ru/maps/?rtext=~{route_str}&rtt=auto"
