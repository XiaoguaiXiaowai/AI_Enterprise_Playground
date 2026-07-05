class HitlPendingError(Exception):
    def __init__(self, hitl_request_id: int):
        super().__init__("hitl_pending")
        self.hitl_request_id = hitl_request_id

