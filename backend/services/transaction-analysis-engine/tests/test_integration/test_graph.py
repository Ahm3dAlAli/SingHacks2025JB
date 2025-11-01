"""
Integration tests for LangGraph workflow orchestration.
Tests the complete 5-agent workflow end-to-end.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.workflows.workflow import TAEWorkflow, execute_workflow
from app.workflows.state import create_initial_state


@pytest.mark.asyncio
class TestTAEWorkflow:
    """Test complete TAE workflow orchestration"""

    async def test_workflow_execution_success(
        self,
        mock_db_session,
        sample_transaction,
        mock_groq_response_rule_parser,
        mock_groq_response_explainer,
    ):
        """Test complete workflow execution with all 5 agents"""
        # Mock all database queries and Groq client
        with patch("app.workflows.agents.rule_parser.get_regulatory_rules") as mock_get_rules:
            with patch("app.workflows.agents.rule_parser.get_groq_client") as mock_rule_groq:
                with patch("app.workflows.agents.explainer.get_groq_client") as mock_exp_groq:
                    with patch(
                        "app.workflows.workflow.static_rules_agent"
                    ) as mock_static:
                        with patch(
                            "app.workflows.workflow.behavioral_agent"
                        ) as mock_behavioral:
                            with patch(
                                "app.workflows.workflow.risk_scorer_agent"
                            ) as mock_risk:
                                # Setup mocks
                                mock_get_rules.return_value = []

                                # Mock Groq clients
                                rule_client = AsyncMock()
                                rule_client.complete = AsyncMock(
                                    return_value=mock_groq_response_rule_parser
                                )
                                mock_rule_groq.return_value = rule_client

                                exp_client = AsyncMock()
                                exp_client.complete = AsyncMock(
                                    return_value=mock_groq_response_explainer
                                )
                                mock_exp_groq.return_value = exp_client

                                # Mock agent returns with correct types
                                mock_static.return_value = []  # List[RuleViolation]
                                mock_behavioral.return_value = []  # List[BehavioralFlag]
                                mock_risk.return_value = (50, "MEDIUM", "Basic explanation")  # Tuple[int, str, str]

                                # Execute workflow
                                workflow = TAEWorkflow(mock_db_session)
                                result = await workflow.execute(sample_transaction)

                                # Verify all agents executed
                                assert result["transaction"] == sample_transaction
                                assert "parsed_rules" in result
                                assert "risk_score" in result
                                assert "alert_level" in result
                                assert "explanation" in result
                                assert "regulatory_citations" in result
                                assert "recommended_action" in result

    async def test_workflow_agent_order(
        self, mock_db_session, sample_transaction, mock_groq_response_rule_parser
    ):
        """Test that agents execute in correct order"""
        execution_order = []

        async def track_execution(name):
            execution_order.append(name)

        # Mock agents to track execution order - patch where they're USED, not defined
        with patch("app.workflows.agents.rule_parser.get_regulatory_rules") as mock_get_rules:
            with patch("app.workflows.agents.rule_parser.get_groq_client") as mock_groq:
                with patch(
                    "app.workflows.workflow.static_rules_agent"
                ) as mock_static:
                    with patch("app.workflows.workflow.behavioral_agent") as mock_behavioral:
                        with patch("app.workflows.workflow.risk_scorer_agent") as mock_risk:
                            with patch("app.workflows.workflow.explainer_agent") as mock_explainer:
                                # Setup mocks with tracking
                                mock_get_rules.return_value = []

                                groq_client = AsyncMock()
                                groq_client.complete = AsyncMock(
                                    return_value=mock_groq_response_rule_parser
                                )
                                mock_groq.return_value = groq_client

                                async def static_side_effect(*args, **kwargs):
                                    await track_execution("static_rules")
                                    return []  # Returns List[RuleViolation]

                                async def behavioral_side_effect(*args, **kwargs):
                                    await track_execution("behavioral")
                                    return []  # Returns List[BehavioralFlag]

                                async def risk_side_effect(*args, **kwargs):
                                    await track_execution("risk_scorer")
                                    # Returns Tuple[int, str, str]
                                    return (50, "MEDIUM", "Test")

                                async def explainer_side_effect(*args, **kwargs):
                                    await track_execution("explainer")
                                    return {
                                        "explanation": "Test explanation",
                                        "regulatory_basis": [],
                                        "evidence": [],
                                        "recommended_action": "MONITORING_ONLY",
                                        "confidence": "MEDIUM",
                                    }

                                mock_static.side_effect = static_side_effect
                                mock_behavioral.side_effect = behavioral_side_effect
                                mock_risk.side_effect = risk_side_effect
                                mock_explainer.side_effect = explainer_side_effect

                                # Execute workflow
                                workflow = TAEWorkflow(mock_db_session)
                                await workflow.execute(sample_transaction)

                                # Verify execution order
                                # Agent 2 & 3 run in parallel, so either order is valid
                                # But risk_scorer must be after both static and behavioral
                                # And explainer must be last
                                assert "static_rules" in execution_order
                                assert "behavioral" in execution_order
                                assert "risk_scorer" in execution_order
                                assert "explainer" in execution_order

                                # Risk scorer must come after both static and behavioral
                                risk_index = execution_order.index("risk_scorer")
                                static_index = execution_order.index("static_rules")
                                behavioral_index = execution_order.index("behavioral")
                                assert risk_index > static_index
                                assert risk_index > behavioral_index

                                # Explainer must be last
                                assert execution_order[-1] == "explainer"

    async def test_workflow_error_handling(self, mock_db_session, sample_transaction):
        """Test workflow error handling when agents fail"""
        # Mock rule parser to fail
        with patch("app.workflows.agents.rule_parser.get_regulatory_rules") as mock_get_rules:
            mock_get_rules.side_effect = Exception("Database error")

            with patch("app.workflows.workflow.static_rules_agent") as mock_static:
                with patch("app.workflows.workflow.behavioral_agent") as mock_behavioral:
                    with patch("app.workflows.workflow.risk_scorer_agent") as mock_risk:
                        with patch("app.workflows.workflow.explainer_agent") as mock_explainer:
                            # Setup other mocks with correct return types
                            mock_static.return_value = []  # List[RuleViolation]
                            mock_behavioral.return_value = []  # List[BehavioralFlag]
                            mock_risk.return_value = (0, "LOW", "Test")  # Tuple[int, str, str]
                            mock_explainer.return_value = {
                                "explanation": "Test",
                                "regulatory_basis": [],
                                "evidence": [],
                                "recommended_action": "MONITORING_ONLY",
                                "confidence": "LOW",
                            }

                            # Execute workflow - should not raise exception
                            workflow = TAEWorkflow(mock_db_session)
                            result = await workflow.execute(sample_transaction)

                            # Workflow should complete despite Agent 1 failure
                            assert result is not None
                            assert "risk_score" in result

    async def test_execute_workflow_convenience_function(
        self, mock_db_session, sample_transaction, mock_groq_response_rule_parser, mock_groq_response_explainer
    ):
        """Test execute_workflow convenience function"""
        with patch("app.workflows.agents.rule_parser.get_regulatory_rules") as mock_get_rules:
            with patch("app.workflows.agents.rule_parser.get_groq_client") as mock_rule_groq:
                with patch("app.workflows.agents.explainer.get_groq_client") as mock_exp_groq:
                    with patch("app.workflows.workflow.static_rules_agent") as mock_static:
                        with patch("app.workflows.workflow.behavioral_agent") as mock_behavioral:
                            with patch("app.workflows.workflow.risk_scorer_agent") as mock_risk:
                                # Setup mocks
                                mock_get_rules.return_value = []

                                rule_client = AsyncMock()
                                rule_client.complete = AsyncMock(return_value=mock_groq_response_rule_parser)
                                mock_rule_groq.return_value = rule_client

                                exp_client = AsyncMock()
                                exp_client.complete = AsyncMock(return_value=mock_groq_response_explainer)
                                mock_exp_groq.return_value = exp_client

                                # Setup mocks with correct return types
                                mock_static.return_value = []  # List[RuleViolation]
                                mock_behavioral.return_value = []  # List[BehavioralFlag]
                                mock_risk.return_value = (75, "HIGH", "Test")  # Tuple[int, str, str]

                                # Execute using convenience function
                                result = await execute_workflow(sample_transaction, mock_db_session)

                                # Verify result structure
                                assert "transaction_id" in result
                                assert "risk_score" in result
                                assert result["risk_score"] == 75
                                assert result["alert_level"] == "HIGH"
                                assert "explanation" in result
                                assert "recommended_action" in result
