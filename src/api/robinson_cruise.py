"""Handler for robinson_cruise endpoint."""

import heapq
import math
from typing import Any, Dict, List, Optional, Tuple


def simulate_edge(
    distance: float,
    mass_shuttle: float,
    mass_fuel_unit: float,
    power_per_unit: float,
    fuel_available: int,
    fuel_consumption: float,
    gravity_assist: Optional[dict] = None
) -> Tuple[float, int, bool]:
    """
    Simulate flight along a single edge.
    
    Args:
        distance: Distance to travel in meters
        mass_shuttle: Mass of the shuttle without fuel (kg)
        mass_fuel_unit: Mass of one fuel unit (kg)
        power_per_unit: Thrust power per fuel unit (N)
        fuel_available: Available fuel units
        fuel_consumption: Fuel consumption coefficient
        gravity_assist: Optional gravity assist parameters
        
    Returns:
        Tuple of (flight_time_seconds, remaining_fuel, success)
    """
    # Stage 1: Takeoff
    fuel_takeoff = math.ceil(fuel_consumption * mass_shuttle / mass_fuel_unit)
    if fuel_available < fuel_takeoff:
        return (0, fuel_available, False)
    
    fuel_remaining = fuel_available - fuel_takeoff
    time_elapsed = 1.0  # Takeoff takes 1 second
    
    # Stage 2: Acceleration
    # Burn half_fuel = fuel_remaining // 2 units
    half_fuel = fuel_remaining // 2
    velocity = 0.0
    distance_covered = 0.0
    current_fuel = fuel_remaining
    
    for _ in range(half_fuel):
        if distance_covered >= distance / 2:
            break
        # Each unit decreases shuttle mass and provides acceleration
        current_mass = mass_shuttle + current_fuel * mass_fuel_unit
        acceleration = power_per_unit / current_mass
        velocity += acceleration  # Applied for 1 second
        distance_covered += velocity  # s += v after acceleration
        current_fuel -= 1
        time_elapsed += 1.0
    
    # Stage 3: Gravity assist (optional, only after acceleration completes)
    if gravity_assist is not None:
        velocity_gain = gravity_assist.get('velocity_gain', 0)
        ga_fuel_cost = gravity_assist.get('fuel_consumption', 0)
        ga_time = gravity_assist.get('time_to_execute', 0)
        
        if current_fuel >= ga_fuel_cost:
            velocity += velocity_gain
            current_fuel -= ga_fuel_cost
            time_elapsed += ga_time
    
    # Stage 4: Coasting (inertia) - cover remaining distance at current velocity
    # We need to cover: distance - distance_covered before starting to brake
    # But braking will also cover some distance while slowing down
    # So coasting_distance = distance - distance_covered - braking_distance_estimate
    
    # For simplicity: coast until we need to start braking
    # The remaining distance to cover is: distance - distance_covered
    remaining_distance = distance - distance_covered
    
    # Stage 5: Braking - burn all remaining fuel to stop at destination
    # Calculate how much distance we'll cover during braking
    # and whether we can stop in time
    
    braking_distance = 0.0
    braking_velocity = velocity
    fuel_used_for_braking = 0
    
    # Simulate braking step by step
    temp_fuel = current_fuel
    temp_v = braking_velocity
    temp_s = 0.0
    
    for i in range(temp_fuel):
        current_mass = mass_shuttle + (temp_fuel - i) * mass_fuel_unit
        deceleration = power_per_unit / current_mass
        
        if temp_v - deceleration <= 0:
            # Would go negative or exactly zero - this is the last effective braking step
            # On the last second: if braking would make v < 0, engines work fraction of second
            # but still consume 1 fuel and 1 second
            temp_s += temp_v  # Add distance covered at current velocity before stopping
            temp_v = 0
            fuel_used_for_braking = i + 1
            break
        
        temp_v -= deceleration
        temp_s += temp_v
        fuel_used_for_braking = i + 1
    
    braking_distance = temp_s
    final_braking_velocity = temp_v
    
    # Check if we can successfully complete the journey
    # Total distance covered = distance_covered (accel) + coasting + braking_distance
    # We need: distance_covered + coasting + braking_distance >= distance
    # And we need final velocity = 0
    
    if final_braking_velocity != 0:
        # Couldn't stop completely with available fuel
        return (0, fuel_available, False)
    
    # Calculate coasting distance needed
    coasting_distance = remaining_distance - braking_distance
    
    if coasting_distance < 0:
        # We would overshoot even without coasting - can't complete successfully
        return (0, fuel_available, False)
    
    # Add coasting time (at constant velocity)
    if coasting_distance > 0 and velocity > 0:
        coasting_time = coasting_distance / velocity
        time_elapsed += coasting_time
    
    # All fuel used for braking is consumed
    remaining_fuel = current_fuel - fuel_used_for_braking
    
    # Success!
    return (round(time_elapsed, 1), remaining_fuel, True)


def process_robinson_cruise(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process robinson_cruise request using modified Dijkstra algorithm.
    
    Args:
        data: The validated input data
        
    Returns:
        Response dictionary with can_reach field
    """
    # Extract parameters
    mass_shuttle = data['mass_shuttle']
    mass_fuel_unit = data['mass_fuel_unit']
    power_per_unit = data['power_per_unit']
    oxygen_time = data['oxygen_time']
    total_fuel = data['total_fuel']
    fuel_consumption = data['fuel_consumption']
    bodies = data['bodies']
    edges = data['edges']
    
    start_point = 'start_point'
    rescue_point = 'rescue_point'
    
    # Build adjacency list and body lookup
    body_map: Dict[str, List[dict]] = {}
    for body in bodies:
        body_map[body['id']] = body.get('gravity_assists', [])
    
    # Adjacency list: node -> list of (to_node, distance)
    adj: Dict[str, List[Tuple[str, float]]] = {}
    for edge in edges:
        from_node = edge.get('from_', edge.get('from'))
        to_node = edge['to']
        dist = edge['distance']
        if from_node not in adj:
            adj[from_node] = []
        adj[from_node].append((to_node, dist))
    
    # Check if start has any outgoing edges
    if start_point not in adj or len(adj[start_point]) == 0:
        return {"can_reach": False}
    
    # Modified Dijkstra: state = (node, remaining_fuel)
    # Priority = accumulated_time
    # heap entries: (accumulated_time, node, remaining_fuel, path)
    
    initial_fuel = total_fuel
    
    # Check takeoff cost from start
    fuel_takeoff = math.ceil(fuel_consumption * mass_shuttle / mass_fuel_unit)
    if initial_fuel < fuel_takeoff:
        return {"can_reach": False}
    
    # Priority queue: (time, node, fuel, path)
    pq = [(0.0, start_point, initial_fuel, [start_point])]
    
    # Best known: (node, fuel) -> min_time
    best: Dict[Tuple[str, int], float] = {}
    
    while pq:
        acc_time, node, fuel, path = heapq.heappop(pq)
        
        # Skip if we've found a better path to this state
        state_key = (node, fuel)
        if state_key in best and best[state_key] <= acc_time:
            continue
        best[state_key] = acc_time
        
        # Check if reached destination
        if node == rescue_point:
            return {
                "can_reach": True,
                "min_flight_time": round(acc_time, 1),
                "route": path
            }
        
        # Prune if exceeds oxygen time
        if acc_time > oxygen_time:
            continue
        
        # Explore neighbors
        if node not in adj:
            continue
            
        for to_node, distance in adj[node]:
            # Get gravity assists available at source node
            gravity_assists = body_map.get(node, [])
            
            # Try without gravity assist
            options = [None] + gravity_assists
            
            for ga in options:
                result = simulate_edge(
                    distance=distance,
                    mass_shuttle=mass_shuttle,
                    mass_fuel_unit=mass_fuel_unit,
                    power_per_unit=power_per_unit,
                    fuel_available=fuel,
                    fuel_consumption=fuel_consumption,
                    gravity_assist=ga
                )
                
                flight_time, remaining_fuel, success = result
                
                if success:
                    new_time = acc_time + flight_time
                    if new_time <= oxygen_time:
                        new_state = (to_node, remaining_fuel)
                        if new_state not in best or best[new_state] > new_time:
                            new_path = path + [to_node]
                            heapq.heappush(pq, (new_time, to_node, remaining_fuel, new_path))
    
    return {"can_reach": False}
