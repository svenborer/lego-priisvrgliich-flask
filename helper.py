from config import _config

def get_availability_score(availability):
    if availability in _config['availability']['coming_soon']:
        return 4
    elif availability in _config['availability']['available']:
        return 3
    elif availability in _config['availability']['limited']:
        return 2
    elif availability in _config['availability']['out_of_stock']:
        return 1
    else:
        return 0