import os
CACHE_DIR = "cache"
def setup_cache():
    if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)
