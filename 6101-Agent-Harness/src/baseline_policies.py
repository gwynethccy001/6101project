class FullApprovePolicy:
    name = "full_approve"
    def decide(self, *args, **kwargs):
        return Decision.AUTO_APPROVE

class FullEscalatePolicy:
    name = "full_escalate"
    def decide(self, *args, **kwargs):
        return Decision.ESCALATE

POLICIES = {"full_approve": FullApprovePolicy, "full_escalate": FullEscalatePolicy}
