import threading

# Global locks for shared JSON files to prevent race conditions in parallel generation
presentation_lock = threading.Lock()
analytics_lock = threading.Lock()
