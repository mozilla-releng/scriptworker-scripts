def get_auth_primitives(ship_it_instance_config):
    """Function to grab the primitives needed for shipitapi objects auth"""
    auth = (ship_it_instance_config['username'], ship_it_instance_config['password'])
    api_root = ship_it_instance_config['api_root']
    timeout_in_seconds = int(ship_it_instance_config.get('timeout_in_seconds', 60))

    return (auth, api_root, timeout_in_seconds)
