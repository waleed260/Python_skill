"""
API Contract Validator Skill (Python)
Compares backend type definitions with frontend fetching logic
"""

import re
import os
from typing import Dict, List, NamedTuple
from dataclasses import dataclass
from pathlib import Path

class SchemaField(NamedTuple):
    name: str
    type_hint: str
    required: bool
    nullable: bool

class MismatchDetail(NamedTuple):
    field: str
    issue: str
    severity: str  # 'high' | 'medium' | 'low'
    backend_definition: str
    frontend_usage: str

@dataclass
class ContractDriftReport:
    backend_type: str
    frontend_usage: str
    mismatches: List[MismatchDetail]

class ApiContractValidator:
    """
    Validates the contract between backend type definitions and frontend usage
    """

    def validate_contract(self, backend_type_path: str, frontend_fetch_path: str, type_name: str) -> ContractDriftReport:
        """
        Validates the contract between backend type definitions and frontend usage
        """
        backend_fields = self._extract_backend_fields(backend_type_path, type_name)
        frontend_fields = self._extract_frontend_fields(frontend_fetch_path)

        mismatches = self._compare_contracts(backend_fields, frontend_fields)

        return ContractDriftReport(
            backend_type=type_name,
            frontend_usage=frontend_fetch_path,
            mismatches=mismatches
        )

    def _extract_backend_fields(self, type_path: str, type_name: str) -> Dict[str, SchemaField]:
        """
        Extract field definitions from Python type hints or similar structures
        """
        fields = {}

        with open(type_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for class definitions with type hints (similar to interfaces in TypeScript)
        class_pattern = rf'class\s+{type_name}\s*(:|\s+extends\s+\w+\s*:)'
        class_match = re.search(class_pattern, content)

        if class_match:
            # Extract fields with type hints from the class
            # This is a simplified version - real implementation would parse AST
            field_pattern = r'(\w+)\s*:\s*([^\n=;]+)'
            field_matches = re.findall(field_pattern, content)

            for field_name, field_type in field_matches:
                # Check if field is optional (contains Optional or has default value)
                is_optional = 'Optional' in field_type or '=' in content.split(f'{field_name}:')[1].split('\n')[0]

                fields[field_name] = SchemaField(
                    name=field_name,
                    type_hint=field_type.strip(),
                    required=not is_optional,
                    nullable=is_optional
                )

        # Also look for TypedDict or similar structures
        typed_dict_pattern = rf'{type_name}\s*=\s*TypedDict\s*\([^,]+,\s*\{{([^}}]+)\}}\)'
        typed_dict_match = re.search(typed_dict_pattern, content, re.DOTALL)

        if typed_dict_match:
            dict_content = typed_dict_match.group(1)
            # Extract field definitions from TypedDict
            dict_field_pattern = r"'(\w+)':\s*([^\n,]+)"
            dict_matches = re.findall(dict_field_pattern, dict_content)

            for field_name, field_type in dict_matches:
                is_optional = 'Optional' in field_type
                fields[field_name] = SchemaField(
                    name=field_name,
                    type_hint=field_type.strip(),
                    required=not is_optional,
                    nullable=is_optional
                )

        return fields

    def _extract_frontend_fields(self, frontend_path: str) -> Dict[str, SchemaField]:
        """
        Extract field usage from frontend code
        """
        fields = {}

        with open(frontend_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for property access patterns (obj.field_name)
        property_access_pattern = r'\.(\w+)'
        property_matches = re.findall(property_access_pattern, content)

        for field_name in set(property_matches):
            # Assume direct property access means it's required
            fields[field_name] = SchemaField(
                name=field_name,
                type_hint='any',
                required=True,
                nullable=False
            )

        # Look for dictionary access patterns (obj['field_name'])
        dict_access_pattern = r"\[['\"](\w+)['\"]\]"
        dict_matches = re.findall(dict_access_pattern, content)

        for field_name in set(dict_matches):
            fields[field_name] = SchemaField(
                name=field_name,
                type_hint='any',
                required=True,
                nullable=False
            )

        # Look for destructuring patterns ({ field_name } = obj)
        destructure_pattern = r'\{([^}]+)\}'
        destructure_matches = re.findall(destructure_pattern, content)

        for destructure in destructure_matches:
            individual_fields = re.findall(r'(\w+)', destructure)
            for field_name in individual_fields:
                fields[field_name] = SchemaField(
                    name=field_name,
                    type_hint='any',
                    required=True,
                    nullable=False
                )

        return fields

    def _compare_contracts(self, backend_fields: Dict[str, SchemaField], frontend_fields: Dict[str, SchemaField]) -> List[MismatchDetail]:
        """
        Compare backend and frontend field definitions for mismatches
        """
        mismatches = []

        # Check for fields that exist in backend but not in frontend
        for field_name, backend_field in backend_fields.items():
            if field_name not in frontend_fields:
                # This might be okay - frontend might not need all fields
                continue

            frontend_field = frontend_fields[field_name]

            # Check for requirement mismatches
            if backend_field.required and not frontend_field.required:
                mismatches.append(MismatchDetail(
                    field=field_name,
                    issue='Backend requires field but frontend treats as optional',
                    severity='high',
                    backend_definition=f"Field '{field_name}' is required in backend",
                    frontend_usage=f"Field '{field_name}' is treated as optional in frontend"
                ))

            if not backend_field.required and frontend_field.required:
                mismatches.append(MismatchDetail(
                    field=field_name,
                    issue='Backend makes field optional but frontend expects it',
                    severity='medium',
                    backend_definition=f"Field '{field_name}' is optional in backend",
                    frontend_usage=f"Field '{field_name}' is accessed directly in frontend"
                ))

            # Check for type mismatches (where we have type info)
            if (backend_field.type_hint != frontend_field.type_hint and
                frontend_field.type_hint != 'any'):
                mismatches.append(MismatchDetail(
                    field=field_name,
                    issue='Type mismatch between backend and frontend',
                    severity='high',
                    backend_definition=f"Field '{field_name}' has type {backend_field.type_hint} in backend",
                    frontend_usage=f"Field '{field_name}' has type {frontend_field.type_hint} in frontend"
                ))

        # Check for fields that exist in frontend but not in backend
        for field_name, frontend_field in frontend_fields.items():
            if field_name not in backend_fields:
                mismatches.append(MismatchDetail(
                    field=field_name,
                    issue='Frontend accesses field that does not exist in backend',
                    severity='high',
                    backend_definition=f"Field '{field_name}' does not exist in backend schema",
                    frontend_usage=f"Field '{field_name}' is accessed in frontend"
                ))

        return mismatches

    def generate_drift_report(self, report: ContractDriftReport, output_path: str) -> None:
        """
        Generate a Schema Drift Report
        """
        report_content = f"""# Schema Drift Report

## Contract Overview
- Backend Type: `{report.backend_type}`
- Frontend Usage: `{report.frontend_usage}`
- Total Mismatches: {len(report.mismatches)}

## Issues Found

"""

        if report.mismatches:
            for mismatch in report.mismatches:
                report_content += f"""### {mismatch.severity.upper()}: {mismatch.issue}
- **Field**: `{mismatch.field}`
- **Severity**: {mismatch.severity}
- **Backend Definition**: {mismatch.backend_definition}
- **Frontend Usage**: {mismatch.frontend_usage}

"""
        else:
            report_content += "No contract mismatches found!\n"

        report_content += """
---

*Generated by API Contract Validator Skill*
*Replaces manual cross-referencing between backend and frontend*
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"Schema Drift Report generated at: {output_path}")

    def validate_multiple_contracts(self, contracts: List[Dict]) -> List[ContractDriftReport]:
        """
        Validate multiple contracts at once
        """
        reports = []

        for contract in contracts:
            try:
                report = self.validate_contract(
                    contract['backend_type_path'],
                    contract['frontend_fetch_path'],
                    contract['type_name']
                )
                reports.append(report)
            except Exception as e:
                print(f"Failed to validate contract for {contract['type_name']}: {e}")

        return reports

# Example usage
if __name__ == "__main__":
    # validator = ApiContractValidator()
    # report = validator.validate_contract(
    #     './backend_types.py',
    #     './frontend_api.py',
    #     'User'
    # )
    # validator.generate_drift_report(report, './SCHEMA_DRIFT_REPORT.md')
    pass