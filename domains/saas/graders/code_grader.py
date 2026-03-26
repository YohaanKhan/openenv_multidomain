"""Deterministic SaaS code grader using trajectories and optional DB state."""

from __future__ import annotations

from typing import Iterable

from server.interfaces import BaseGrader


class SaaSCodeGrader(BaseGrader):
    """Scores whether the agent grounded its SaaS workflow on the right records."""

    def grade(self, trajectory: list[dict], session) -> dict:
        if not trajectory:
            return {"score": 0.0, "success": False, "feedback": "Empty trajectory"}

        task = self._infer_task(trajectory)
        if task == "saas_easy":
            return self._grade_easy(trajectory, session)
        if task == "saas_medium":
            return self._grade_medium(trajectory, session)
        if task == "saas_hard":
            return self._grade_hard(trajectory, session)
        return {"score": 0.0, "success": False, "feedback": "Could not infer task"}

    def _infer_task(self, trajectory: Iterable[dict]) -> str | None:
        """Infer task ID from seeded identifiers used in tool calls or tool results."""
        joined = "\n".join(
            f"{step.get('tool_name', '')} {step.get('tool_args', {})} {step.get('result', '')}"
            for step in trajectory
        )
        if any(token in joined for token in ("C-9001", "T-8001", "T-8002", "TX-9802")):
            return "saas_hard"
        if any(token in joined for token in ("C-2077", "T-5002", "TX-9002")):
            return "saas_medium"
        if any(token in joined for token in ("C-1042", "T-5001", "TX-5001")):
            return "saas_easy"
        return None

    def _has_step(self, trajectory: Iterable[dict], tool_name: str, **expected_args) -> bool:
        for step in trajectory:
            if step.get("tool_name") != tool_name:
                continue
            args = step.get("tool_args", {})
            if all(args.get(key) == value for key, value in expected_args.items()):
                return True
        return False

    def _count_wrong_refunds(self, trajectory: Iterable[dict], valid_tx: str, customer_id: str) -> int:
        count = 0
        for step in trajectory:
            if step.get("tool_name") != "issue_refund":
                continue
            args = step.get("tool_args", {})
            if args.get("transaction_id") != valid_tx or args.get("customer_id") != customer_id:
                count += 1
        return count

    def _score_result(self, score: float, success: bool, feedback: str) -> dict:
        bounded = max(0.0, min(1.0, round(score, 4)))
        return {"score": bounded, "success": success, "feedback": feedback}

    def _grade_easy(self, trajectory: list[dict], session) -> dict:
        searched_target = self._has_step(
            trajectory, "search_tickets", customer_id="C-1042"
        ) or self._has_step(trajectory, "get_account", customer_id="C-1042")
        closed_target = self._has_step(trajectory, "close_ticket", ticket_id="T-5001")

        score = 0.0
        if searched_target:
            score += 0.35
        if closed_target:
            score += 0.65

        if session is not None and closed_target:
            from domains.saas.schema import Ticket
            ticket = session.get(Ticket, "T-5001")
            if not ticket or ticket.status != "closed":
                score = min(score, 0.45)
                closed_target = False

        feedback = "Resolved the correct billing ticket." if closed_target else "Did not close T-5001."
        return self._score_result(score, closed_target, feedback)

    def _grade_medium(self, trajectory: list[dict], session) -> dict:
        account_lookup = self._has_step(trajectory, "get_account", customer_id="C-2077")
        searched_ticket = self._has_step(trajectory, "search_tickets", customer_id="C-2077")
        reviewed_transactions = self._has_step(
            trajectory, "get_transactions", customer_id="C-2077"
        )
        refunded_duplicate = self._has_step(
            trajectory,
            "issue_refund",
            customer_id="C-2077",
            transaction_id="TX-9002",
        )
        emailed_customer = self._has_step(trajectory, "send_email", customer_id="C-2077")
        closed_ticket = self._has_step(trajectory, "close_ticket", ticket_id="T-5002")
        wrong_refunds = self._count_wrong_refunds(trajectory, "TX-9002", "C-2077")

        score = 0.0
        if account_lookup or searched_ticket:
            score += 0.15
        if reviewed_transactions:
            score += 0.20
        if refunded_duplicate:
            score += 0.35
        if emailed_customer:
            score += 0.15
        if closed_ticket:
            score += 0.15
        score -= wrong_refunds * 0.20

        success = refunded_duplicate and closed_ticket

        if session is not None and refunded_duplicate:
            from domains.saas.schema import Ticket, Transaction
            tx = session.get(Transaction, "TX-9002")
            ticket = session.get(Ticket, "T-5002")
            if not tx or tx.status != "refunded":
                score = min(score, 0.55)
                success = False
            if not ticket or ticket.status != "closed":
                score = min(score, 0.70)
                success = False

        feedback = "Refunded the duplicate charge and closed the billing ticket."
        if wrong_refunds:
            feedback = "Attempted at least one incorrect refund."
        elif not success:
            feedback = "Partial progress on duplicate-charge workflow."
        return self._score_result(score, success, feedback)

    def _grade_hard(self, trajectory: list[dict], session) -> dict:
        reviewed_account = self._has_step(trajectory, "get_account", customer_id="C-9001")
        searched_vip = self._has_step(trajectory, "search_tickets", customer_id="C-9001")
        reviewed_transactions = self._has_step(
            trajectory, "get_transactions", customer_id="C-9001"
        )
        refunded_duplicate = self._has_step(
            trajectory,
            "issue_refund",
            customer_id="C-9001",
            transaction_id="TX-9802",
        )
        escalated_fraud = self._has_step(
            trajectory,
            "escalate_ticket",
            ticket_id="T-8001",
            tier=2,
        )
        closed_billing = self._has_step(trajectory, "close_ticket", ticket_id="T-8002")
        emailed_customer = self._has_step(trajectory, "send_email", customer_id="C-9001")
        wrong_refunds = self._count_wrong_refunds(trajectory, "TX-9802", "C-9001")
        closed_fraud_ticket = self._has_step(trajectory, "close_ticket", ticket_id="T-8001")

        score = 0.0
        if reviewed_account or searched_vip:
            score += 0.15
        if reviewed_transactions:
            score += 0.15
        if refunded_duplicate:
            score += 0.20
        if escalated_fraud:
            score += 0.20
        if emailed_customer:
            score += 0.10
        if closed_billing:
            score += 0.20
        score -= wrong_refunds * 0.20
        if closed_fraud_ticket:
            score -= 0.20

        success = refunded_duplicate and escalated_fraud and closed_billing and emailed_customer

        if session is not None:
            from domains.saas.schema import Email, Ticket, Transaction
            tx = session.get(Transaction, "TX-9802")
            fraud_ticket = session.get(Ticket, "T-8001")
            billing_ticket = session.get(Ticket, "T-8002")
            email_sent = (
                session.query(Email).filter(Email.customer_id == "C-9001").count() > 0
            )
            if not tx or tx.status != "refunded":
                score = min(score, 0.75)
                success = False
            if not fraud_ticket or fraud_ticket.status != "escalated" or fraud_ticket.tier != 2:
                score = min(score, 0.75)
                success = False
            if not billing_ticket or billing_ticket.status != "closed":
                score = min(score, 0.80)
                success = False
            if not email_sent:
                score = min(score, 0.85)
                success = False

        feedback = "Handled the VIP billing incident with grounded actions."
        if wrong_refunds or closed_fraud_ticket:
            feedback = "Made a risky or incorrect action during VIP incident handling."
        elif not success:
            feedback = "Partial progress on the VIP incident workflow."
        return self._score_result(score, success, feedback)
