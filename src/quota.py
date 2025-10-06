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

def increment_quota(api_call_name):
    """Increments the global quota usage counter and prints the cost."""
    global _QUOTA_USAGE
    cost = QUOTA_COSTS.get(api_call_name, 0)
    if cost > 0:
        _QUOTA_USAGE += cost
        print(f"{T.INFO}   {E.KEY} Quota +{cost} for '{api_call_name}'. Total session usage: {_QUOTA_USAGE}")

def get_total_quota_usage():
    """Returns the total estimated quota usage for the session."""
    return _QUOTA_USAGE

def display_quota_usage():
    """Prints the final estimated quota usage for the session."""
    print(f"\n{T.HEADER}--- {E.REPORT} API Quota Usage Report ---")
    print(f"  Total estimated quota units used in this session: {_QUOTA_USAGE}")
    print(f"  YouTube Data API daily quota is typically 10,000 units.")
    if _QUOTA_USAGE > 9000:
        print(f"{T.WARN}{E.WARN}  Warning: You are approaching or have exceeded the daily quota.")
    print(f"{T.HEADER}------------------------------------")