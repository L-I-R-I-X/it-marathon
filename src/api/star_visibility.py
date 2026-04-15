"""Handler for star_visibility endpoint."""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def get_body_position(
    body: dict,
    t_seconds: float,
    bodies_by_id: dict,
    visited: Optional[set] = None
) -> Tuple[float, float]:
    """
    Calculate position of a celestial body at time t.
    
    Args:
        body: Body dictionary with type, position, orbit info
        t_seconds: Time in seconds from start
        bodies_by_id: Index of bodies by id for parent lookup
        visited: Set of visited body ids to prevent infinite recursion
        
    Returns:
        Tuple of (x, y) coordinates
    """
    if visited is None:
        visited = set()
    
    body_id = body.get("id")
    if body_id is not None:
        if body_id in visited:
            # Cycle detected, return origin to break recursion
            return (0.0, 0.0)
        visited = visited | {body_id}
    
    if body["type"] == "star":
        return (body["position"]["x"], body["position"]["y"])
    else:
        # Get parent position recursively
        parent_id = body.get("parent_id")
        if parent_id is None or parent_id not in bodies_by_id:
            parent_x, parent_y = 0.0, 0.0
        else:
            parent_body = bodies_by_id[parent_id]
            parent_x, parent_y = get_body_position(parent_body, t_seconds, bodies_by_id, visited)
        
        # Calculate angle in radians
        angular_velocity = body.get("angular_velocity", 0)
        initial_angle = body.get("initial_angle", 0)
        rotation_clockwise = body.get("rotation_clockwise", False)
        
        direction = -1 if rotation_clockwise else 1
        angle_rad = math.radians(initial_angle + angular_velocity * t_seconds * direction)
        
        orbit_radius = body.get("orbit_radius", 0)
        x = parent_x + orbit_radius * math.cos(angle_rad)
        y = parent_y + orbit_radius * math.sin(angle_rad)
        
        return (x, y)


def is_star_visible(
    target_vector: Tuple[float, float],
    bodies: List[dict],
    t_seconds: float,
    bodies_by_id: dict
) -> bool:
    """
    Check if the target star is visible at time t.
    
    Args:
        target_vector: Direction vector to the target star (dx, dy)
        bodies: List of celestial bodies that might occlude the star
        t_seconds: Time in seconds from start
        bodies_by_id: Index of bodies by id for position calculation
        
    Returns:
        True if star is visible, False if occluded
    """
    dx, dy = target_vector
    
    # Normalize the direction vector
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        # Invalid zero-length vector, treat as visible
        return True
    
    ux = dx / length
    uy = dy / length
    
    for body in bodies:
        # Skip stars as they don't occlude
        if body.get("type") == "star":
            continue
        
        # Get body position
        cx, cy = get_body_position(body, t_seconds, bodies_by_id)
        
        # Project center onto ray
        proj = cx * ux + cy * uy
        
        # If projection <= 0, body is behind observer
        if proj <= 0:
            continue
        
        # Closest point on ray
        px = proj * ux
        py = proj * uy
        
        # Distance from body center to ray
        dist = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)
        
        # Check if body intersects the ray
        radius = body.get("radius", 0)
        if dist <= radius:
            return False
    
    return True


def find_visibility_window(
    target_vector: Tuple[float, float],
    bodies: List[dict],
    start_timestamp: float,
    required_duration: int,
    time_step: float = 0.5,
    max_wait: float = 1e9
) -> Optional[dict]:
    """
    Find visibility windows for the target star.
    
    Args:
        target_vector: Direction vector to the target star
        bodies: List of celestial bodies
        start_timestamp: Unix timestamp of observation start
        required_duration: Required transmission time in seconds
        time_step: Time step for sampling
        max_wait: Maximum time to search
        
    Returns:
        Dictionary with wait and duration, or None if no suitable window found
    """
    # Build index for quick parent lookup
    bodies_by_id = {body["id"]: body for body in bodies if "id" in body}
    
    # Если нет тел, способных закрывать звезду (пустой список или только звёзды)
    blocking_bodies = [b for b in bodies if b.get("type") in ["planet", "moon"]]
    if not blocking_bodies:
        return {"wait": 0, "duration": "inf"}
    
    # Check initial visibility at t=0
    visible_at_0 = is_star_visible(target_vector, bodies, 0.0, bodies_by_id)
    
    # If blocked at t=0, check if it's permanently blocked
    # by checking if all bodies have angular_velocity=0 and are blocking
    all_stationary = all(b.get("angular_velocity", 0) == 0 for b in blocking_bodies)
    
    if all_stationary:
        # Positions don't change, so visibility is constant
        if visible_at_0:
            return {"wait": 0, "duration": "inf"}
        else:
            return None
    
    # Sample visibility over time
    intervals = []
    t = 0.0
    visible = visible_at_0
    current_start = 0.0 if visible else None
    
    # For rotating bodies, find the period (LCM of all periods)
    # Period = 360 / angular_velocity degrees per second
    periods = []
    for body in blocking_bodies:
        av = body.get("angular_velocity", 0)
        if av != 0:
            period = 360.0 / abs(av)
            periods.append(period)
    
    # Calculate approximate system period (use max period as upper bound for one cycle)
    if periods:
        system_period = max(periods) * 2  # Check at least 2 full cycles
        effective_max_wait = min(max_wait, system_period)
    else:
        effective_max_wait = max_wait
    
    while t < effective_max_wait:
        t += time_step
        new_visible = is_star_visible(target_vector, bodies, t, bodies_by_id)
        
        if visible != new_visible:
            if new_visible:
                # Start of visible interval
                current_start = t
            else:
                # End of visible interval
                if current_start is not None:
                    intervals.append((current_start, t))
                current_start = None
            
            visible = new_visible
    
    # Handle unclosed interval at end
    if current_start is not None:
        intervals.append((current_start, effective_max_wait))
    
    # Check if star never gets occluded (first interval starts at 0 and goes to end)
    first_interval = intervals[0] if intervals else None
    if first_interval and first_interval[0] == 0 and first_interval[1] == effective_max_wait:
        return {"wait": 0, "duration": "inf"}
    
    # Filter intervals by required duration
    suitable_intervals = []
    for start, end in intervals:
        session_start = math.ceil(start)
        session_end = math.floor(end)
        duration = session_end - session_start
        
        if duration >= required_duration:
            suitable_intervals.append((session_start, duration))
    
    if not suitable_intervals:
        return None
    
    # Select interval with minimum wait time
    best = min(suitable_intervals, key=lambda x: x[0])
    return {"wait": best[0], "duration": best[1]}


def process_star_visibility(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process star_visibility request.
    
    Args:
        data: The validated input data containing:
            - target_star_vector: {"x": float, "y": float}
            - celestial_bodies: list of bodies with hierarchy
            - observation_params: {"start_time": ISO8601, "required_transmission_time": int}
        
    Returns:
        Response dictionary with found field and optional timing info
    """
    # Parse input data
    target_star_vector = data["target_star_vector"]
    celestial_bodies = data["celestial_bodies"]
    observation_params = data["observation_params"]
    
    target_vector = (target_star_vector["x"], target_star_vector["y"])
    required_duration = observation_params["required_transmission_time"]
    
    # Parse start_time (not used in calculation but required by spec)
    start_time_str = observation_params["start_time"]
    start_timestamp = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc).timestamp()
    
    # Find visibility window
    result = find_visibility_window(
        target_vector=target_vector,
        bodies=celestial_bodies,
        start_timestamp=start_timestamp,
        required_duration=required_duration
    )
    
    if result is None:
        return {"found": False}
    
    # Обработка "инфинита" в ответе
    if result["duration"] == "inf":
        duration_value = "inf"
    else:
        duration_value = int(result["duration"])  # целое число секунд
    
    return {
        "found": True,
        "next_fitting_interval_in": int(result["wait"]),
        "interval_duration": duration_value
    }
