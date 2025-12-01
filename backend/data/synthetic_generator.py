#!/usr/bin/env python3
"""
Synthetic Test Data Generator

Generates diverse PII test cases using Faker for benchmark evaluation.
Creates realistic employee query scenarios with exact entity positions.

Usage:
    python synthetic_generator.py
    python synthetic_generator.py --count 500
    python synthetic_generator.py --output synthetic_500.json
"""

import argparse
import json
import random
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from faker import Faker
from faker.providers import BaseProvider


# Custom provider for salary and financial data
class FinancialProvider(BaseProvider):
    """Custom Faker provider for financial/HR data."""

    def salary(self, min_val: int = 45000, max_val: int = 250000) -> str:
        """Generate a salary in common formats."""
        amount = random.randint(min_val // 1000, max_val // 1000) * 1000
        formats = [
            f"${amount:,}",
            f"${amount:,}/year",
            f"${amount:,} annually",
            f"${amount:,} per year",
            f"${amount/12:,.0f}/month",
        ]
        return random.choice(formats)

    def salary_range(self) -> str:
        """Generate a salary range."""
        base = random.randint(50, 200) * 1000
        high = base + random.randint(10, 50) * 1000
        return f"${base:,} - ${high:,}"

    def bank_account(self) -> str:
        """Generate a US bank account number."""
        length = random.choice([8, 9, 10, 12])
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

    def routing_number(self) -> str:
        """Generate a bank routing number."""
        return ''.join([str(random.randint(0, 9)) for _ in range(9)])


@dataclass
class Entity:
    """Represents a PII entity with position information."""
    text: str
    entity_type: str
    start: int = 0
    end: int = 0

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end
        }


@dataclass
class TestCase:
    """Represents a complete test case."""
    id: str
    category: str
    difficulty: str
    query: str
    expected_entities: List[Entity] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category,
            "difficulty": self.difficulty,
            "query": self.query,
            "expected_entities": [e.to_dict() for e in self.expected_entities],
            "tags": self.tags
        }


class SyntheticGenerator:
    """Generates synthetic PII test cases using Faker."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize with optional seed for reproducibility."""
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        # Initialize primary Faker (single locale for custom providers)
        self.fake = Faker('en_US')
        self.fake.add_provider(FinancialProvider)

        # Additional English locale fakers for name diversity
        self.fake_en = [Faker('en_US'), Faker('en_GB'), Faker('en_CA'), Faker('en_AU')]

        # Additional fakers for international names
        self.fake_intl = {
            'es': Faker('es_ES'),
            'de': Faker('de_DE'),
            'fr': Faker('fr_FR'),
            'it': Faker('it_IT'),
            'ja': Faker('ja_JP'),
            'zh': Faker('zh_CN'),
            'ko': Faker('ko_KR'),
            'pt': Faker('pt_BR'),
        }

        self.case_counter = 0

    def _diverse_name(self) -> str:
        """Get a name from a random English locale for diversity."""
        faker = random.choice(self.fake_en)
        return faker.name()

    def _find_entity_position(self, query: str, entity_text: str,
                               start_from: int = 0) -> Tuple[int, int]:
        """Find exact position of entity in query."""
        start = query.find(entity_text, start_from)
        if start == -1:
            # Try case-insensitive search
            lower_query = query.lower()
            lower_entity = entity_text.lower()
            start = lower_query.find(lower_entity, start_from)

        if start == -1:
            raise ValueError(f"Entity '{entity_text}' not found in query")

        end = start + len(entity_text)
        return start, end

    def _create_entity(self, query: str, text: str, entity_type: str,
                       start_from: int = 0) -> Entity:
        """Create an entity with calculated positions."""
        start, end = self._find_entity_position(query, text, start_from)
        return Entity(text=text, entity_type=entity_type, start=start, end=end)

    def _generate_id(self, prefix: str = "SYN") -> str:
        """Generate unique test case ID."""
        self.case_counter += 1
        return f"{prefix}-{self.case_counter:04d}"

    # =========================================================================
    # Template Categories
    # =========================================================================

    def generate_compensation_query(self) -> TestCase:
        """Generate compensation/salary related query."""
        name = self.fake.name()
        salary = self.fake.salary()

        templates = [
            f"What is {name}'s current salary of {salary}?",
            f"Employee {name} earns {salary} per year.",
            f"Looking up compensation for {name}: {salary}",
            f"{name} has a base salary of {salary}.",
            f"Verify {name}'s annual compensation: {salary}",
            f"The salary for {name} is set at {salary}.",
            f"Update records: {name} now makes {salary}.",
            f"Confirm {name}'s pay rate of {salary}.",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, salary, "SALARY"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="compensation",
            difficulty="easy",
            query=query,
            expected_entities=entities,
            tags=["salary", "synthetic"]
        )

    def generate_contact_query(self) -> TestCase:
        """Generate contact information query."""
        name = self.fake.name()
        email = self.fake.email()
        phone = self.fake.phone_number()

        # Clean phone to common formats
        phone_clean = re.sub(r'x\d+', '', phone).strip()

        templates = [
            f"Contact {name} at {email} or {phone_clean}.",
            f"{name}'s email is {email} and phone is {phone_clean}.",
            f"Reach out to {name}: {email}, {phone_clean}",
            f"Employee contact - {name}: {email} / {phone_clean}",
            f"For {name}, use email {email} or call {phone_clean}.",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, email, "EMAIL_ADDRESS"),
            self._create_entity(query, phone_clean, "PHONE_NUMBER"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="contact",
            difficulty="easy",
            query=query,
            expected_entities=entities,
            tags=["contact", "email", "phone", "synthetic"]
        )

    def generate_ssn_query(self) -> TestCase:
        """Generate SSN-related query."""
        name = self.fake.name()
        ssn = self.fake.ssn()

        templates = [
            f"Verify SSN for {name}: {ssn}",
            f"{name}'s social security number is {ssn}.",
            f"SSN lookup: {name} - {ssn}",
            f"Employee {name} has SSN {ssn} on file.",
            f"Update W-4 for {name}, SSN: {ssn}",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, ssn, "US_SSN"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="payroll",
            difficulty="medium",
            query=query,
            expected_entities=entities,
            tags=["ssn", "sensitive", "synthetic"]
        )

    def generate_banking_query(self) -> TestCase:
        """Generate direct deposit/banking query."""
        name = self.fake.name()
        bank_account = self.fake.bank_account()
        routing = self.fake.routing_number()

        templates = [
            f"Direct deposit for {name}: routing {routing}, account {bank_account}.",
            f"{name}'s bank info - Routing: {routing}, Account: {bank_account}",
            f"Set up ACH for {name} with account {bank_account}, routing {routing}.",
            f"Banking details for {name}: {routing} / {bank_account}",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, bank_account, "US_BANK_NUMBER"),
        ]
        # Note: Routing numbers are often not flagged as PII in Presidio

        return TestCase(
            id=self._generate_id(),
            category="payroll",
            difficulty="medium",
            query=query,
            expected_entities=entities,
            tags=["banking", "direct_deposit", "synthetic"]
        )

    def generate_full_profile_query(self) -> TestCase:
        """Generate comprehensive employee profile query."""
        name = self.fake.name()
        email = self.fake.email()
        phone = self.fake.phone_number()
        phone_clean = re.sub(r'x\d+', '', phone).strip()
        ssn = self.fake.ssn()
        salary = self.fake.salary()
        dob = self.fake.date_of_birth(minimum_age=22, maximum_age=65).strftime("%m/%d/%Y")
        address = self.fake.address().replace('\n', ', ')

        templates = [
            f"Employee profile: {name}, {email}, {phone_clean}, DOB: {dob}, SSN: {ssn}, Salary: {salary}",
            f"Full record for {name} - Email: {email}, Phone: {phone_clean}, Born: {dob}, SSN: {ssn}, Compensation: {salary}",
            f"{name} | {email} | {phone_clean} | {dob} | {ssn} | {salary}",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, email, "EMAIL_ADDRESS"),
            self._create_entity(query, phone_clean, "PHONE_NUMBER"),
            self._create_entity(query, dob, "DATE_TIME"),
            self._create_entity(query, ssn, "US_SSN"),
            self._create_entity(query, salary, "SALARY"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="comprehensive",
            difficulty="hard",
            query=query,
            expected_entities=entities,
            tags=["full_profile", "multi_pii", "synthetic"]
        )

    def generate_onboarding_query(self) -> TestCase:
        """Generate new hire onboarding query."""
        name = self.fake.name()
        email = self.fake.email()
        start_date = self.fake.future_date(end_date="+60d").strftime("%B %d, %Y")
        salary = self.fake.salary()

        templates = [
            f"New hire: {name} starting {start_date} at {salary}. Email: {email}",
            f"Onboarding {name} ({email}) - Start: {start_date}, Salary: {salary}",
            f"Welcome packet for {name}, joining {start_date} with compensation {salary}. Contact: {email}",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, start_date, "DATE_TIME"),
            self._create_entity(query, salary, "SALARY"),
            self._create_entity(query, email, "EMAIL_ADDRESS"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="onboarding",
            difficulty="medium",
            query=query,
            expected_entities=entities,
            tags=["onboarding", "new_hire", "synthetic"]
        )

    def generate_address_query(self) -> TestCase:
        """Generate address-related query."""
        name = self.fake.name()
        street = self.fake.street_address()
        city = self.fake.city()
        state = self.fake.state_abbr()
        zipcode = self.fake.zipcode()
        full_address = f"{street}, {city}, {state} {zipcode}"

        templates = [
            f"Mail W-2 to {name} at {full_address}.",
            f"{name}'s mailing address: {full_address}",
            f"Ship equipment to {name}, {full_address}",
            f"Address update for {name}: {full_address}",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            # Note: Full address detection varies by detector
        ]

        # Add location entity for city/state
        try:
            city_entity = self._create_entity(query, city, "LOCATION")
            entities.append(city_entity)
        except ValueError:
            pass

        return TestCase(
            id=self._generate_id(),
            category="contact",
            difficulty="medium",
            query=query,
            expected_entities=entities,
            tags=["address", "location", "synthetic"]
        )

    def generate_international_name_query(self) -> TestCase:
        """Generate query with international name."""
        locale = random.choice(list(self.fake_intl.keys()))
        faker = self.fake_intl[locale]

        name = faker.name()
        salary = self.fake.salary()
        email = f"{name.lower().replace(' ', '.').replace(',', '')}@company.com"
        # Simplify email for matching
        email = re.sub(r'[^a-zA-Z0-9.@]', '', email)

        templates = [
            f"International employee {name} earns {salary}.",
            f"Record for {name}: compensation {salary}",
            f"{name}'s salary is {salary}.",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, salary, "SALARY"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="international",
            difficulty="hard",
            query=query,
            expected_entities=entities,
            tags=["international", f"locale_{locale}", "synthetic"]
        )

    def generate_credit_card_query(self) -> TestCase:
        """Generate credit card related query."""
        name = self.fake.name()
        cc = self.fake.credit_card_number()

        templates = [
            f"Corporate card for {name}: {cc}",
            f"{name}'s expense card number: {cc}",
            f"Update payment method for {name} - Card: {cc}",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, cc, "CREDIT_CARD"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="financial",
            difficulty="medium",
            query=query,
            expected_entities=entities,
            tags=["credit_card", "financial", "synthetic"]
        )

    def generate_multiple_people_query(self) -> TestCase:
        """Generate query with multiple people."""
        name1 = self.fake.name()
        name2 = self.fake.name()
        salary1 = self.fake.salary()
        salary2 = self.fake.salary()

        templates = [
            f"Compare salaries: {name1} ({salary1}) vs {name2} ({salary2})",
            f"Team compensation - {name1}: {salary1}, {name2}: {salary2}",
            f"{name1} earns {salary1} while {name2} makes {salary2}.",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name1, "PERSON"),
            self._create_entity(query, salary1, "SALARY"),
            self._create_entity(query, name2, "PERSON"),
            self._create_entity(query, salary2, "SALARY"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="comprehensive",
            difficulty="hard",
            query=query,
            expected_entities=entities,
            tags=["multiple_people", "comparison", "synthetic"]
        )

    def generate_negative_query(self) -> TestCase:
        """Generate safe query with no PII."""
        templates = [
            "What are the company holidays for this year?",
            "How do I submit a vacation request?",
            "What is the dress code policy?",
            "Where can I find the employee handbook?",
            "What are the core business hours?",
            "How do I reset my password?",
            "What benefits are available to employees?",
            "How do I request a parking pass?",
            "What is the procedure for reporting an issue?",
            "Where is the cafeteria located?",
            "What training programs are available?",
            "How do I join the wellness program?",
            "What is the policy on remote work?",
            "How do I update my emergency contact?",
            "What are the performance review dates?",
            "How do I access the company intranet?",
            "What is the process for internal transfers?",
            "How do I request office supplies?",
            "What is the visitor policy?",
            "How do I book a conference room?",
        ]

        query = random.choice(templates)

        return TestCase(
            id=self._generate_id(),
            category="negative",
            difficulty="easy",
            query=query,
            expected_entities=[],
            tags=["safe", "no_pii", "synthetic"]
        )

    def generate_edge_case_query(self) -> TestCase:
        """Generate edge case with potential false positives."""
        edge_cases = [
            # Names that look like common words
            ("April May works in HR.", "April May", "PERSON"),
            ("Summer Winter joined the team.", "Summer Winter", "PERSON"),
            ("Bill Cash handles payroll.", "Bill Cash", "PERSON"),
            ("Will Power leads motivation training.", "Will Power", "PERSON"),
            ("Crystal Ball does forecasting.", "Crystal Ball", "PERSON"),
            # Names with numbers nearby
            ("Room 101 is booked by John.", "John", "PERSON"),
            ("Section 8 housing inquiry.", None, None),  # False positive risk
            # Mixed content
            ("The 401k plan offers matching.", None, None),
            ("Meet at Building 5 at 10:00 AM.", None, None),
            # Partial matches
            ("Email support@company.com for help.", "support@company.com", "EMAIL_ADDRESS"),
        ]

        case = random.choice(edge_cases)
        query = case[0]

        entities = []
        if case[1] is not None:
            try:
                entities.append(self._create_entity(query, case[1], case[2]))
            except ValueError:
                pass

        return TestCase(
            id=self._generate_id(),
            category="edge_case",
            difficulty="hard",
            query=query,
            expected_entities=entities,
            tags=["edge_case", "potential_fp", "synthetic"]
        )

    def generate_date_query(self) -> TestCase:
        """Generate date-focused query."""
        name = self.fake.name()
        dob = self.fake.date_of_birth(minimum_age=22, maximum_age=65)

        # Various date formats
        date_formats = [
            dob.strftime("%m/%d/%Y"),
            dob.strftime("%B %d, %Y"),
            dob.strftime("%Y-%m-%d"),
            dob.strftime("%d %B %Y"),
        ]
        date_str = random.choice(date_formats)

        templates = [
            f"{name} was born on {date_str}.",
            f"DOB for {name}: {date_str}",
            f"Birthday: {name} - {date_str}",
            f"Verify birth date of {name}: {date_str}",
        ]

        query = random.choice(templates)
        entities = [
            self._create_entity(query, name, "PERSON"),
            self._create_entity(query, date_str, "DATE_TIME"),
        ]

        return TestCase(
            id=self._generate_id(),
            category="personal",
            difficulty="medium",
            query=query,
            expected_entities=entities,
            tags=["date", "dob", "synthetic"]
        )

    # =========================================================================
    # Main Generation Methods
    # =========================================================================

    def generate_cases(self, count: int = 300) -> List[TestCase]:
        """Generate specified number of test cases with balanced distribution."""
        cases = []

        # Define distribution (weights should sum to ~1.0)
        generators = [
            (self.generate_compensation_query, 0.15),      # 15%
            (self.generate_contact_query, 0.12),           # 12%
            (self.generate_ssn_query, 0.08),               # 8%
            (self.generate_banking_query, 0.06),           # 6%
            (self.generate_full_profile_query, 0.10),      # 10%
            (self.generate_onboarding_query, 0.08),        # 8%
            (self.generate_address_query, 0.06),           # 6%
            (self.generate_international_name_query, 0.08),# 8%
            (self.generate_credit_card_query, 0.05),       # 5%
            (self.generate_multiple_people_query, 0.05),   # 5%
            (self.generate_negative_query, 0.10),          # 10%
            (self.generate_edge_case_query, 0.04),         # 4%
            (self.generate_date_query, 0.03),              # 3%
        ]

        # Calculate counts for each generator
        remaining = count
        for gen_func, weight in generators[:-1]:
            gen_count = int(count * weight)
            for _ in range(gen_count):
                try:
                    cases.append(gen_func())
                except Exception as e:
                    print(f"Warning: Failed to generate case: {e}")
            remaining -= gen_count

        # Fill remaining with random selection
        for _ in range(remaining):
            gen_func = random.choice([g[0] for g in generators])
            try:
                cases.append(gen_func())
            except Exception as e:
                print(f"Warning: Failed to generate case: {e}")

        # Shuffle to mix categories
        random.shuffle(cases)

        # Re-number IDs after shuffle
        for i, case in enumerate(cases, 1):
            case.id = f"SYN-{i:04d}"

        return cases

    def save_to_json(self, cases: List[TestCase], filepath: str) -> None:
        """Save test cases to JSON file."""
        data = {
            "metadata": {
                "name": "Synthetic PII Test Dataset",
                "description": "Auto-generated test cases using Faker",
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_cases": len(cases),
                "categories": list(set(c.category for c in cases)),
            },
            "test_cases": [c.to_dict() for c in cases]
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Generated {len(cases)} test cases")
        print(f"Saved to: {filepath}")

        # Print category distribution
        categories = {}
        for case in cases:
            categories[case.category] = categories.get(case.category, 0) + 1
        print("\nCategory distribution:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count} ({count/len(cases)*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic PII test data")
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=300,
        help="Number of test cases to generate (default: 300)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data/synthetic_dataset.json",
        help="Output file path (default: data/synthetic_dataset.json)"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    # Resolve path relative to script location
    script_dir = Path(__file__).parent
    output_path = script_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)

    generator = SyntheticGenerator(seed=args.seed)
    cases = generator.generate_cases(count=args.count)
    generator.save_to_json(cases, str(output_path))


if __name__ == "__main__":
    main()
