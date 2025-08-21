from backend.services.routing import load_city_graph, best_route, RiskMode
import os

def test_route_balanced():
    gp = load_city_graph(os.path.join(os.path.dirname(__file__), '..', 'config', 'city_graph.json'))
    plan = best_route('LYMHURST','MARTLOCK', RiskMode.balanced, 'OX_T6', 0.6)
    assert plan and plan['minutes_est'] > 0 and 'nodes' in plan

def test_route_royal_blocks_red():
    gp = load_city_graph(os.path.join(os.path.dirname(__file__), '..', 'config', 'city_graph.json'))
    plan = best_route('CAERLEON','LYMHURST', RiskMode.royal_only, 'OX_T6', 0.6)
    assert plan is None
