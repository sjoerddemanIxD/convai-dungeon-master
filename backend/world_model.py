
def deep_merge(source, destination):
    """
    Recursively merges source dict into destination dict.
    Overwrites existing keys in destination.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # Get node or create one
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination

class WorldModel:
    def __init__(self, initial_state=None):
        if initial_state is None:
            initial_state = {
                "location": {
                    "name": "Unknown",
                    "description": "A dimly lit space. Details are sparse."
                },
                "characters": {},
                "objects": {},
                "event_history": []
            }
        self.state = initial_state

    def get_state(self):
        return self.state

    def update_state(self, updates):
        """
        Deep merges updates into the current state.
        """
        deep_merge(updates, self.state)

    def add_event(self, event_string):
        self.state["event_history"].append(event_string)
        # Optional: trim history to keep it from getting too long
        if len(self.state["event_history"]) > 20:
            self.state["event_history"].pop(0)

    def get_context_for_prompt(self):
        # Return a simplified version of the state for the AI prompt
        return {
            "location": self.state.get("location"),
            "characters": self.state.get("characters"),
            "objects": self.state.get("objects"),
            "recent_events": self.state.get("event_history", [])[-5:] # Last 5 events
        }
