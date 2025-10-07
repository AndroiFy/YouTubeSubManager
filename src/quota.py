from src.config import T, E

_QUOTA_USAGE = 0

# Based on https://developers.google.com/youtube/v3/determine_quota_cost
QUOTA_COSTS = {
    'channels.list': 1,
    'playlistItems.list': 1,
    'captions.list': 50,
    'captions.insert': 400,
    'captions.update': 450,
    'captions.delete': 50,
}

def increment_quota(api_call_name, translator):
    """Increments the global quota usage counter and prints the cost."""
    global _QUOTA_USAGE
    cost = QUOTA_COSTS.get(api_call_name, 0)
    if cost > 0:
        _QUOTA_USAGE += cost
        print(translator.get('quota.increment', T_INFO=T.INFO, E_KEY=E.KEY, cost=cost, api_call_name=api_call_name, total_usage=_QUOTA_USAGE))

def get_total_quota_usage():
    """Returns the total estimated quota usage for the session."""
    return _QUOTA_USAGE

def display_quota_usage(translator):
    """Prints the final estimated quota usage for the session."""
    print(translator.get('quota.report_header', T_HEADER=T.HEADER, E_REPORT=E.REPORT))
    print(translator.get('quota.report_total', total_usage=_QUOTA_USAGE))
    print(translator.get('quota.report_limit_info'))
    if _QUOTA_USAGE > 9000:
        print(translator.get('quota.report_warning', T_WARN=T.WARN, E_WARN=E.WARN))
    print(translator.get('quota.report_footer', T_HEADER=T.HEADER))