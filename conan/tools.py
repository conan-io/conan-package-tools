
def get_bool_from_env(var_name):
    import os
    val = os.getenv(var_name, None)
    return val not in (None, "0", "None", "False")
