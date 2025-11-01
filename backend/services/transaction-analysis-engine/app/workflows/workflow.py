"""
LangGraph workflow orchestration for Transaction Analysis Engine.
Coordinates all 5 agents in the correct sequence with parallel execution where possible.

Workflow:
    Agent 1 (Rule Parser)
        ↓
    Agent 2 (Static Rules) ↓ Agent 3 (Behavioral) [PARALLEL]
        ↓
    Agent 4 (Risk Scorer)
        ↓
    Agent 5 (Explainer)
"""

from typing import Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.state import (
    TAEState,
    create_initial_state,
    update_state_with_parsed_rules,
    update_state_with_static_violations,
    update_state_with_behavioral_flags,
    update_state_with_risk_assessment,
    update_state_with_explanation_details,
)
from app.workflows.agents import (
    rule_parser_agent,
    static_rules_agent,
    behavioral_agent,
    risk_scorer_agent,
    explainer_agent,
)
from app.database.models import Transaction
from app.utils.logger import logger


class TAEWorkflow:
    """
    Transaction Analysis Engine workflow manager.
    Orchestrates all 5 agents using LangGraph.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize workflow with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow with all agents and edges.

        Returns:
            Compiled StateGraph ready for execution
        """
        # Create workflow
        workflow = StateGraph(TAEState)

        # Add nodes
        workflow.add_node("rule_parser", self._rule_parser_node)
        workflow.add_node("static_rules", self._static_rules_node)
        workflow.add_node("behavioral", self._behavioral_node)
        workflow.add_node("risk_scorer", self._risk_scorer_node)
        workflow.add_node("explainer", self._explainer_node)

        # Set entry point
        workflow.set_entry_point("rule_parser")

        # Define edges
        # Agent 1 → Agent 2 & 3 (parallel)
        workflow.add_edge("rule_parser", "static_rules")
        workflow.add_edge("rule_parser", "behavioral")

        # Agent 2 & 3 → Agent 4
        workflow.add_edge("static_rules", "risk_scorer")
        workflow.add_edge("behavioral", "risk_scorer")

        # Agent 4 → Agent 5
        workflow.add_edge("risk_scorer", "explainer")

        # Agent 5 → END
        workflow.add_edge("explainer", END)

        # Compile and return
        return workflow.compile()

    async def _rule_parser_node(self, state: TAEState) -> TAEState:
        """
        Node wrapper for Agent 1: Rule Parser.
        Parses regulatory rules using Groq LLM.

        Args:
            state: Current TAEState

        Returns:
            Updated TAEState with parsed_rules
        """
        try:
            logger.info(
                f"Executing Agent 1 (Rule Parser) for transaction {state['transaction'].transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "node": "rule_parser",
                    }
                },
            )

            # Call agent
            result = await rule_parser_agent(state["transaction"], self.session)

            # Return only the fields this node updates
            return {
                "parsed_rules": result,
            }

        except Exception as e:
            logger.error(
                f"Error in rule_parser node: {str(e)}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "error": str(e),
                    }
                },
            )
            # Return only updated fields with empty parsed_rules (fail gracefully)
            return {
                "parsed_rules": {"parsed_rules": []},
            }

    async def _static_rules_node(self, state: TAEState) -> TAEState:
        """
        Node wrapper for Agent 2: Static Rules Engine.
        Checks transactions against regulatory compliance rules.

        Args:
            state: Current TAEState

        Returns:
            Updated TAEState with regulatory_rules and static_violations
        """
        try:
            logger.info(
                f"Executing Agent 2 (Static Rules) for transaction {state['transaction'].transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "node": "static_rules",
                    }
                },
            )

            # Call agent (returns List[RuleViolation])
            violations = await static_rules_agent(state["transaction"], self.session)

            # Return only the fields this node updates
            return {
                "static_violations": violations,
                "regulatory_rules": [],  # Not fetched by this agent
            }

        except Exception as e:
            logger.error(
                f"Error in static_rules node: {str(e)}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "error": str(e),
                    }
                },
            )
            # Return only updated fields with empty violations (fail gracefully)
            return {
                "regulatory_rules": [],
                "static_violations": [],
            }

    async def _behavioral_node(self, state: TAEState) -> TAEState:
        """
        Node wrapper for Agent 3: Behavioral Pattern Analyzer.
        Detects suspicious behavioral patterns.

        Args:
            state: Current TAEState

        Returns:
            Updated TAEState with behavioral_flags
        """
        try:
            logger.info(
                f"Executing Agent 3 (Behavioral) for transaction {state['transaction'].transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "node": "behavioral",
                    }
                },
            )

            # Call agent (returns List[BehavioralFlag])
            flags = await behavioral_agent(state["transaction"], self.session)

            # Return only the fields this node updates
            return {
                "behavioral_flags": flags,
            }

        except Exception as e:
            logger.error(
                f"Error in behavioral node: {str(e)}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "error": str(e),
                    }
                },
            )
            # Return only updated fields with empty flags (fail gracefully)
            return {
                "behavioral_flags": [],
            }

    async def _risk_scorer_node(self, state: TAEState) -> TAEState:
        """
        Node wrapper for Agent 4: Risk Scorer.
        Aggregates all findings into final risk score.

        Args:
            state: Current TAEState

        Returns:
            Updated TAEState with risk_score, alert_level, explanation
        """
        try:
            logger.info(
                f"Executing Agent 4 (Risk Scorer) for transaction {state['transaction'].transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "node": "risk_scorer",
                        "violations_count": len(state.get("static_violations", [])),
                        "flags_count": len(state.get("behavioral_flags", [])),
                    }
                },
            )

            # Call agent (returns Tuple[int, str, str])
            risk_score, alert_level, explanation = await risk_scorer_agent(
                transaction=state["transaction"],
                violations=state.get("static_violations", []),
                flags=state.get("behavioral_flags", []),
                session=self.session,
            )

            # Return only the fields this node updates
            return {
                "risk_score": risk_score,
                "alert_level": alert_level,
                "explanation": explanation,
            }

        except Exception as e:
            logger.error(
                f"Error in risk_scorer node: {str(e)}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "error": str(e),
                    }
                },
            )
            # Return only updated fields with default risk score (fail gracefully)
            return {
                "risk_score": 0,
                "alert_level": "LOW",
                "explanation": "Risk scoring failed, defaulting to LOW",
            }

    async def _explainer_node(self, state: TAEState) -> TAEState:
        """
        Node wrapper for Agent 5: Explainer.
        Generates audit-ready explanation using Groq LLM.

        Args:
            state: Current TAEState

        Returns:
            Updated TAEState with enhanced explanation, regulatory_citations, recommended_action, confidence
        """
        try:
            logger.info(
                f"Executing Agent 5 (Explainer) for transaction {state['transaction'].transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "node": "explainer",
                        "risk_score": state.get("risk_score", 0),
                        "alert_level": state.get("alert_level", "LOW"),
                    }
                },
            )

            # Call agent
            result = await explainer_agent(
                transaction=state["transaction"],
                session=self.session,
                risk_score=state.get("risk_score", 0),
                alert_level=state.get("alert_level", "LOW"),
                static_violations=state.get("static_violations", []),
                behavioral_flags=state.get("behavioral_flags", []),
            )

            # Return only the fields this node updates
            return {
                "explanation": result["explanation"],
                "regulatory_citations": result["regulatory_basis"],
                "recommended_action": result["recommended_action"],
                "confidence": result["confidence"],
            }

        except Exception as e:
            logger.error(
                f"Error in explainer node: {str(e)}",
                extra={
                    "extra_data": {
                        "transaction_id": str(state["transaction"].transaction_id),
                        "error": str(e),
                    }
                },
            )
            # Return only updated fields with basic explanation (fail gracefully)
            return {
                "regulatory_citations": [],
                "recommended_action": "MONITORING_ONLY",
                "confidence": "LOW",
                # Keep existing explanation from Agent 4
            }

    async def execute(self, transaction: Transaction) -> TAEState:
        """
        Execute the complete workflow for a single transaction.

        Args:
            transaction: Transaction to analyze

        Returns:
            Final TAEState with all analysis results

        Example:
            >>> workflow = TAEWorkflow(session)
            >>> result = await workflow.execute(transaction)
            >>> result["risk_score"]
            85
        """
        start_time = datetime.utcnow()

        logger.info(
            f"Starting TAE workflow for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "customer_id": transaction.customer_id,
                    "amount": float(transaction.amount),
                    "jurisdiction": transaction.booking_jurisdiction,
                }
            },
        )

        # Create initial state
        initial_state = create_initial_state(transaction)

        # Execute workflow
        final_state = await self.graph.ainvoke(initial_state)

        # Calculate total execution time
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"TAE workflow completed for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "execution_time_ms": execution_time_ms,
                    "risk_score": final_state.get("risk_score", 0),
                    "alert_level": final_state.get("alert_level", "UNKNOWN"),
                    "recommended_action": final_state.get("recommended_action", "UNKNOWN"),
                }
            },
        )

        return final_state


async def execute_workflow(
    transaction: Transaction, session: AsyncSession
) -> Dict[str, Any]:
    """
    Convenience function to execute TAE workflow for a single transaction.

    Args:
        transaction: Transaction to analyze
        session: Database session for queries and logging

    Returns:
        Dictionary with final analysis results

    Example:
        >>> result = await execute_workflow(transaction, session)
        >>> result["risk_score"]
        85
    """
    workflow = TAEWorkflow(session)
    final_state = await workflow.execute(transaction)

    # Convert to dict for easy consumption
    return {
        "transaction_id": str(final_state["transaction"].transaction_id),
        "risk_score": final_state["risk_score"],
        "alert_level": final_state["alert_level"],
        "explanation": final_state["explanation"],
        "static_violations": [v.model_dump() for v in final_state.get("static_violations", [])],
        "behavioral_flags": [f.model_dump() for f in final_state.get("behavioral_flags", [])],
        "regulatory_citations": final_state.get("regulatory_citations", []),
        "recommended_action": final_state.get("recommended_action"),
        "confidence": final_state.get("confidence"),
        "parsed_rules": final_state.get("parsed_rules"),
    }
