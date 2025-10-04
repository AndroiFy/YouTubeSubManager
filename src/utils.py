from src.config import T, E, QUOTA_COSTS
from src.translations import get_string

def confirm_quota(uploads=0, updates=0, deletes=0):
    """Calculates estimated quota cost and asks for user confirmation."""
    total_cost = (uploads * QUOTA_COSTS.get('UPLOAD', 0) +
                  updates * QUOTA_COSTS.get('UPDATE', 0) +
                  deletes * QUOTA_COSTS.get('DELETE', 0))

    if total_cost == 0:
        return True

    print(f"{T.WARN}⚠️ {get_string('quota_warning', uploads=uploads, updates=updates, deletes=deletes, total_cost=total_cost)}")
    print(f"{T.INFO}   {get_string('quota_details', percentage=f'{(total_cost / 10000) * 100:.1f}')}")

    proceed = input(f"{T.INFO}   {get_string('quota_proceed')} ").lower()
    if proceed not in ['y', 'yes']:
        print(f"{T.FAIL}{E.FAIL} {get_string('operation_aborted')}")
        return False
    return True