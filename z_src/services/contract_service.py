"""
Contract Service - Contract domain business logic

This service orchestrates:
- AI extraction
- Document processing
- Tool calculations
- Business rules

It's domain-specific - knows about contracts.
"""

from langfuse import observe
from .ai_service import AIService
from .document_service import DocumentService
from tools.date_calculator import DateCalculator
from tools.amount_calculator import AmountCalculator


class ContractService:
    """Service for contract analysis and operations."""

    def __init__(self, model: str = "gemini-2.5-flash-lite"):
        """Initialize contract service with dependencies.

        Args:
            model: Gemini model to use
        """
        # Initialize dependencies
        self.ai_service = AIService(model=model)
        self.doc_service = DocumentService()
        self.date_calc = DateCalculator()
        self.amount_calc = AmountCalculator()

    @observe()
    def analyze_contract(self, file_bytes: bytes) -> dict:
        """Complete contract analysis pipeline.

        This is the main entry point for contract analysis.
        It orchestrates all the steps needed.

        Args:
            file_bytes: PDF contract file bytes

        Returns:
            Complete contract data with analysis

        Raises:
            Exception: If analysis fails
        """
        # Validate document
        self.doc_service.validate_pdf(file_bytes)

        # Extract structured data using AI
        schema = self._get_contract_schema()
        data = self.ai_service.extract_structured(file_bytes, schema)

        # Add calculated fields using tools
        data = self._enrich_contract_data(data)

        return data

    @observe()
    def answer_question(self, question: str, contract_data: dict) -> str:
        """Answer question about a contract.

        Args:
            question: User's question
            contract_data: Contract data for context

        Returns:
            AI's answer
        """
        system_instruction = """You are a legal contract analyst assistant.
Answer questions accurately based on the provided contract data.
If information is not in the contract, say so."""

        return self.ai_service.chat_with_context(
            question,
            contract_data,
            system_instruction
        )

    @observe()
    def compare_contracts(self, contract1: dict, contract2: dict) -> dict:
        """Compare two contracts and highlight differences.

        Args:
            contract1: First contract data
            contract2: Second contract data

        Returns:
            Comparison analysis
        """
        # This would use AI service to compare
        # For now, return basic comparison
        return {
            "party_diff": set(contract1.get("parties", [])) != set(contract2.get("parties", [])),
            "amount_diff": contract1.get("payment_amount") != contract2.get("payment_amount"),
            "dates_diff": (
                contract1.get("effective_date") != contract2.get("effective_date") or
                contract1.get("expiration_date") != contract2.get("expiration_date")
            )
        }

    def _get_contract_schema(self) -> dict:
        """Define contract extraction schema.

        Returns:
            JSON schema for contract data
        """
        return {
            "parties": ["list of party names"],
            "effective_date": "YYYY-MM-DD or null",
            "expiration_date": "YYYY-MM-DD or null",
            "payment_amount": "number or null",
            "payment_frequency": "string (monthly, annual, etc.) or null",
            "payment_currency": "string (USD, EUR, etc.) or null",
            "key_obligations": ["list of main obligations"],
            "termination_clause": "string or null",
            "governing_law": "string (jurisdiction) or null"
        }

    @observe()
    def _enrich_contract_data(self, data: dict) -> dict:
        """Add calculated fields to contract data.

        Args:
            data: Basic contract data

        Returns:
            Enriched contract data
        """
        # Calculate date-related fields
        if data.get('expiration_date'):
            data['days_until_expiry'] = self.date_calc.days_until(
                data['expiration_date']
            )
            data['is_expired'] = data['days_until_expiry'] < 0
            data['renewal_date'] = self.date_calc.get_renewal_date(
                data['expiration_date'],
                days_before=90
            )

        # Calculate financial fields
        if all([
            data.get('payment_amount'),
            data.get('payment_frequency'),
            data.get('effective_date'),
            data.get('expiration_date')
        ]):
            data['total_value'] = self.amount_calc.calculate_total_value(
                amount=data['payment_amount'],
                frequency=data['payment_frequency'],
                start_date=data['effective_date'],
                end_date=data['expiration_date']
            )

        return data
