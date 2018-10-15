import os


def get_bool_from_env(var_name):
    import os
    val = os.getenv(var_name, None)
    return val not in (None, "0", "None", "False")


def split_colon_env(varname):
    if os.getenv(varname) is None:
        return None
    if os.getenv(varname).strip() == "":
        return []
    return [a.strip() for a in list(filter(None, os.getenv(varname, "").split(",")))]
