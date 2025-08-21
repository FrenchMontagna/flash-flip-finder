from typing import Dict, Any, List, Optional, Tuple
import json
from heapq import heappush, heappop
from enum import StrEnum

class RiskMode(StrEnum):
    royal_only = 'royal_only'
    balanced = 'balanced'
    aggressive = 'aggressive'

MOUNT_SPEED_MPM = {
    'OX_T6': 1.0,
    'HORSE_T5': 1.4,
    'STALLION_T8': 1.6,
}

RISK_WEIGHT = {
    RiskMode.royal_only: 1.0,
    RiskMode.balanced: 0.5,
    RiskMode.aggressive: 0.2,
}

_graph = None

def load_city_graph(path: str) -> Dict[str, Any]:
    global _graph
    with open(path, 'r') as f:
        _graph = json.load(f)
    adj: Dict[str, List[Dict[str, Any]]] = {c: [] for c in _graph['cities']}
    defaults = _graph.get('defaults', {})
    hop_base = defaults.get('hop_base_minutes', 4.0)
    for e in _graph['edges']:
        frm = e['from'].upper().replace(' ', '_')
        to = e['to'].upper().replace(' ', '_')
        if frm not in adj: adj[frm] = []
        if to not in adj: adj[to] = []
        base_minutes = e.get('base_minutes') or (e.get('distance_hops', 1) * hop_base)
        rec = {
            'from': frm, 'to': to,
            'zone_type': e.get('zone_type', 'yellow'),
            'distance_hops': e.get('distance_hops', 1),
            'base_minutes': base_minutes,
            'risk_factor': e.get('risk_factor', _graph['defaults']['risk_factors'].get(e.get('zone_type', 'yellow'), 0.2))
        }
        adj[frm].append(rec)
        rev = rec.copy(); rev['from'], rev['to'] = to, frm
        adj[to].append(rev)
    _graph['adj'] = adj
    _graph['hop_base_minutes'] = hop_base
    return _graph

def mount_speed(mount: str) -> float:
    return MOUNT_SPEED_MPM.get(mount, 1.0)

def risk_weight(mode: RiskMode) -> float:
    return RISK_WEIGHT[mode]

def edges_from(node: str) -> List[Dict[str, Any]]:
    return _graph['adj'].get(node, [])

def derive_risk_label(nodes: List[str]) -> str:
    colors = []
    for i in range(len(nodes)-1):
        u, v = nodes[i], nodes[i+1]
        for e in edges_from(u):
            if e['to'] == v:
                colors.append(e['zone_type']); break
    if 'black' in colors: return 'high'
    if 'red' in colors: return 'med'
    return 'low'

def edge_cost(edge: Dict[str, Any], risk_mode: RiskMode, mount_speed_mpm: float, load_pct: float, risk_w: float) -> float:
    base = edge.get('base_minutes') or _graph['hop_base_minutes']
    load_penalty = 1.0 + 0.5*max(0.0, load_pct - 0.5)
    time = base / max(0.5, mount_speed_mpm) * load_penalty
    if risk_mode == RiskMode.royal_only and edge.get('zone_type') in ('red','black'):
        return float('inf')
    return time * (1.0 + risk_w * edge.get('risk_factor', 0.2))

def best_route(from_city: str, to_city: str, risk_mode: RiskMode, mount: str, load_pct: float) -> Optional[Dict[str, Any]]:
    if from_city not in _graph['adj'] or to_city not in _graph['adj']:
        return None
    pq: List[Tuple[float, str, List[str]]] = []
    heappush(pq, (0.0, from_city, []))
    seen: Dict[str, float] = {}
    risk_w = risk_weight(risk_mode)
    mspd = mount_speed(mount)

    while pq:
        cost, node, path = heappop(pq)
        if node == to_city:
            nodes = path + [node]
            return {
                'risk_mode': risk_mode.value,
                'nodes': nodes,
                'minutes_est': round(cost, 2),
                'risk_label': derive_risk_label(nodes),
                'mount_suggested': mount,
                'max_load_pct': round(load_pct, 2),
            }
        if node in seen and seen[node] <= cost:
            continue
        seen[node] = cost
        for e in edges_from(node):
            c = edge_cost(e, risk_mode, mspd, load_pct, risk_w)
            if c == float('inf'):
                continue
            heappush(pq, (cost + c, e['to'], path + [node]))
    return None
