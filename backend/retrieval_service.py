"""
Retrieval Service for RAG (Retrieval-Augmented Generation).
Handles employee data lookup and context building for the LLM.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Any


class RetrievalService:
    """
    Service for retrieving employee data based on query content.
    Supports name-based lookup and context building for RAG.
    """

    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize the retrieval service with employee data.

        Args:
            data_path: Path to employees.json file. If None, uses default location.
        """
        if data_path is None:
            data_path = Path(__file__).parent / "data" / "employees.json"

        with open(data_path, "r") as f:
            data = json.load(f)

        self.company = data.get("company", "Company")
        self.employees: List[Dict[str, Any]] = data.get("employees", [])

        # Build indexes for fast lookup
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build various indexes for efficient employee lookup."""
        # Full name index (case-insensitive)
        self.name_index: Dict[str, Dict] = {}

        # First name index
        self.first_name_index: Dict[str, List[Dict]] = {}

        # Last name index
        self.last_name_index: Dict[str, List[Dict]] = {}

        # Department index
        self.department_index: Dict[str, List[Dict]] = {}

        for emp in self.employees:
            name = emp["name"]
            name_lower = name.lower()

            # Full name
            self.name_index[name_lower] = emp

            # First and last name
            parts = name.split()
            if parts:
                first = parts[0].lower()
                if first not in self.first_name_index:
                    self.first_name_index[first] = []
                self.first_name_index[first].append(emp)

                if len(parts) > 1:
                    last = parts[-1].lower()
                    if last not in self.last_name_index:
                        self.last_name_index[last] = []
                    self.last_name_index[last].append(emp)

            # Department
            dept = emp.get("department", "").lower()
            if dept:
                if dept not in self.department_index:
                    self.department_index[dept] = []
                self.department_index[dept].append(emp)

    def find_employees_in_query(self, query: str) -> List[Dict]:
        """
        Find all employees mentioned in a query.

        Args:
            query: The user's query text

        Returns:
            List of employee records that were mentioned
        """
        query_lower = query.lower()
        mentioned = []
        seen_ids = set()

        # Check for full names first (most specific)
        for name, emp in self.name_index.items():
            if name in query_lower and emp["id"] not in seen_ids:
                mentioned.append(emp)
                seen_ids.add(emp["id"])

        # Check for first names (if not already matched by full name)
        for first_name, employees in self.first_name_index.items():
            # Use word boundary matching to avoid partial matches
            pattern = rf"\b{re.escape(first_name)}\b"
            if re.search(pattern, query_lower):
                for emp in employees:
                    if emp["id"] not in seen_ids:
                        mentioned.append(emp)
                        seen_ids.add(emp["id"])

        return mentioned

    def find_by_department(self, department: str) -> List[Dict]:
        """
        Find all employees in a specific department.

        Args:
            department: Department name (case-insensitive)

        Returns:
            List of employee records in that department
        """
        return self.department_index.get(department.lower(), [])

    def detect_department_query(self, query: str) -> Optional[str]:
        """
        Detect if the query is asking about a specific department.

        Args:
            query: The user's query text

        Returns:
            Department name if detected, None otherwise
        """
        query_lower = query.lower()

        # Check for department names in query
        for dept in self.department_index.keys():
            if dept in query_lower:
                return dept

        return None

    def build_rag_context(self, employees: List[Dict], include_sensitive: bool = True) -> str:
        """
        Build a context string from employee records for the LLM.

        Args:
            employees: List of employee records to include
            include_sensitive: Whether to include sensitive PII fields

        Returns:
            Formatted context string
        """
        if not employees:
            return ""

        context_parts = [f"Employee Records from {self.company}:"]

        for emp in employees:
            parts = [
                f"- {emp['name']}: {emp['title']}, {emp['department']}"
            ]

            if include_sensitive:
                parts.append(f"  Salary: {emp['salary']}")
                parts.append(f"  Email: {emp['email']}")
                parts.append(f"  Phone: {emp['phone']}")
                if emp.get("dob"):
                    parts.append(f"  DOB: {emp['dob']}")
                if emp.get("address"):
                    parts.append(f"  Address: {emp['address']}")

            context_parts.extend(parts)

        return "\n".join(context_parts)

    def get_employee_by_id(self, employee_id: str) -> Optional[Dict]:
        """
        Get an employee record by ID.

        Args:
            employee_id: The employee ID (e.g., "EMP001")

        Returns:
            Employee record or None if not found
        """
        for emp in self.employees:
            if emp["id"] == employee_id:
                return emp
        return None

    def get_all_employees(self) -> List[Dict]:
        """Get all employee records."""
        return self.employees

    def get_salary_ranking(self, top_n: Optional[int] = None) -> List[Dict]:
        """
        Get employees ranked by salary (highest first).

        Args:
            top_n: If provided, return only top N employees

        Returns:
            List of employees sorted by salary (descending)
        """
        def parse_salary(salary_str: str) -> float:
            """Parse salary string to float for comparison."""
            # Remove $ and , then convert
            cleaned = salary_str.replace("$", "").replace(",", "")
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        sorted_employees = sorted(
            self.employees,
            key=lambda e: parse_salary(e.get("salary", "0")),
            reverse=True
        )

        if top_n:
            return sorted_employees[:top_n]
        return sorted_employees

    def retrieve_for_query(self, query: str) -> Dict[str, Any]:
        """
        Main retrieval method - analyzes query and retrieves relevant context.

        Args:
            query: The user's query text

        Returns:
            Dict containing:
                - employees: List of relevant employee records
                - context: Formatted context string for LLM
                - retrieval_type: Type of retrieval performed
        """
        result = {
            "employees": [],
            "context": "",
            "retrieval_type": "none"
        }

        # Check for comparison/ranking queries
        query_lower = query.lower()

        # Detect "top N" or "highest" queries
        if any(term in query_lower for term in ["top", "highest", "most", "best paid"]):
            # Extract number if present
            numbers = re.findall(r"\d+", query)
            top_n = int(numbers[0]) if numbers else 3

            result["employees"] = self.get_salary_ranking(top_n)
            result["context"] = self.build_rag_context(result["employees"])
            result["retrieval_type"] = "ranking"
            return result

        # Check for department queries
        dept = self.detect_department_query(query)
        if dept and any(term in query_lower for term in ["all", "everyone", "employees in", "compare", "salaries"]):
            result["employees"] = self.find_by_department(dept)
            result["context"] = self.build_rag_context(result["employees"])
            result["retrieval_type"] = "department"
            return result

        # Check for specific employee mentions
        mentioned = self.find_employees_in_query(query)
        if mentioned:
            result["employees"] = mentioned
            result["context"] = self.build_rag_context(mentioned)
            result["retrieval_type"] = "named"
            return result

        return result


# Singleton instance
retrieval_service = RetrievalService()
