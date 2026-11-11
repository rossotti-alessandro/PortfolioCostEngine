"""Accuracy evaluation protocol (SC-9.1): one way to score every extraction strategy.

Stages, each scored separately so an error is attributed to the stage that made it:
classification -> field extraction -> provenance (the cited box really holds the value) ->
portfolio computation (totals against pinned golden numbers) -> invariants (missing is never
zero, no double counting, every counted cost traceable). Protocol: docs/EVALUATION_PROTOCOL.md.
"""
