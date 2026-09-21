"""
Microstructure Memory

Stores snapshots and later attaches validation results.
"""

class MicrostructureMemory:

    def __init__(self):
        self.snapshots = {}

    def store(self, snapshot):

        self.snapshots[
            snapshot.snapshot_id
        ] = snapshot.to_dict()

        return snapshot.snapshot_id


    def update_result(
        self,
        snapshot_id,
        result
    ):

        if snapshot_id not in self.snapshots:
            return False

        self.snapshots[snapshot_id]["validation"] = result

        return True


    def get(self, snapshot_id):

        return self.snapshots.get(snapshot_id)


    def all(self):

        return list(self.snapshots.values())
