import collections


# From https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d
