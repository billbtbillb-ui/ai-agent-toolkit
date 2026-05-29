#!/usr/bin/env python3
\"\"\"DB Migration - compare schemas and generate migration scripts.\"\"\"

import argparse
import json
import os
import re
import sys
import hashlib
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Column:
    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    is_primary_key: bool = False
    is_unique: bool = False
    check_constraint: Optional[str] = None
    comment: str = ""


@dataclass
class Index:
    name: str
    columns: list
    unique: bool = False
    method: str = "btree"  # btree, hash, gist, gin, brin
    where_clause: Optional[str] = None


@dataclass
class ForeignKey:
    name: str
    columns: list
    ref_table: str
    ref_columns: list
    on_delete: str = "NO ACTION"
    on_update: str = "NO ACTION"


@dataclass
class Table:
    name: str
    columns: list = field(default_factory=list)
    indexes: list = field(default_factory=list)
    foreign_keys: list = field(default_factory=list)
    primary_key: list = field(default_factory=list)
    comment: str = ""


@dataclass
class Schema:
    tables: dict = field(default_factory=dict)  # name -> Table
    views: dict = field(default_factory=dict)
    sequences: dict = field(default_factory=dict)
    extensions: list = field(default_factory=list)
    database_type: str = "unknown"
    version: str = ""


def parse_sql_schema(sql: str, dialect: str = "postgresql") -> Schema:
    \"\"\"Parse SQL DDL into Schema object.\"\"\"
    schema = Schema(database_type=dialect)
    
    # Simple regex-based parser for common DDL patterns
    # CREATE TABLE
    table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:"?)(\w+)(?:"?)\s*\((.*?)\);'
    
    tables = {}
    for match in re.finditer(table_pattern, sql, re.DOTALL | re.IGNORECASE):
        table_name = match.group(1)
        body = match.group(2)
        table = Table(name=table_name)
        
        # Parse columns and constraints
        # Split by comma, respecting parentheses
        parts = _split_ddl_parts(body)
        for part in parts:
            part = part.strip()
            
            # PRIMARY KEY constraint
            if re.match(r'PRIMARY\s+KEY', part, re.IGNORECASE):
                pk_match = re.search(r'\((.+?)\)', part)
                if pk_match:
                    table.primary_key = [c.strip().strip('"') for c in pk_match.group(1).split(',')]
                continue
            
            # FOREIGN KEY constraint
            if re.match(r'(?:CONSTRAINT\s+\w+\s+)?FOREIGN\s+KEY', part, re.IGNORECASE):
                # Simplified FK parsing
                continue
            
            # UNIQUE constraint
            if re.match(r'(?:CONSTRAINT\s+\w+\s+)?UNIQUE', part, re.IGNORECASE):
                continue
            
            # CHECK constraint
            if re.match(r'(?:CONSTRAINT\s+\w+\s+)?CHECK', part, re.IGNORECASE):
                continue
            
            # Regular column: "name TYPE [constraints]"
            col_match = re.match(r'(?:"?)(\w+)(?:"?)\s+(\w+(?:\([^)]+\))?)\s*(.*)', part, re.IGNORECASE)
            if col_match:
                col_name = col_match.group(1)
                col_type = col_match.group(2).upper()
                rest = col_match.group(3)
                
                col = Column(name=col_name, data_type=col_type)
                
                if 'NOT NULL' in rest.upper():
                    col.nullable = False
                if 'PRIMARY KEY' in rest.upper():
                    col.is_primary_key = True
                    table.primary_key.append(col_name)
                if 'UNIQUE' in rest.upper():
                    col.is_unique = True
                default_match = re.search(r'DEFAULT\s+(.+?)(?:\s|$)', rest, re.IGNORECASE)
                if default_match:
                    col.default = default_match.group(1).rstrip(',')
                
                table.columns.append(col)
        
        tables[table_name] = table
    
    schema.tables = tables
    return schema


def _split_ddl_parts(body: str) -> list:
    \"\"\"Split DDL body by comma, respecting nested parentheses.\"\"\"
    parts = []
    depth = 0
    current = []
    for char in body:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
            continue
        current.append(char)
    if current:
        parts.append(''.join(current))
    return parts


def compare_schemas(source: Schema, target: Schema) -> dict:
    \"\"\"Compare two schemas and return differences.\"\"\"
    diffs = {
        "new_tables": [],
        "dropped_tables": [],
        "modified_tables": [],
        "new_columns": [],
        "dropped_columns": [],
        "modified_columns": [],
        "new_indexes": [],
        "dropped_indexes": [],
        "risk_assessment": {},
    }
    
    src_tables = set(source.tables.keys())
    tgt_tables = set(target.tables.keys())
    
    # New tables
    for name in tgt_tables - src_tables:
        diffs["new_tables"].append({"name": name, "risk": "Safe"})
    
    # Dropped tables
    for name in src_tables - tgt_tables:
        diffs["dropped_tables"].append({"name": name, "risk": "Breaking", "warning": "Data will be lost!"})
    
    # Modified tables
    for name in src_tables & tgt_tables:
        src_table = source.tables[name]
        tgt_table = target.tables[name]
        
        src_cols = {c.name: c for c in src_table.columns}
        tgt_cols = {c.name: c for c in tgt_table.columns}
        
        # New columns
        for col_name in tgt_cols - src_cols:
            col = tgt_cols[col_name]
            risk = "Caution" if not col.nullable and col.default is None else "Safe"
            diffs["new_columns"].append({
                "table": name,
                "column": col_name,
                "type": col.data_type,
                "nullable": col.nullable,
                "default": col.default,
                "risk": risk,
            })
        
        # Dropped columns
        for col_name in src_cols - tgt_cols:
            diffs["dropped_columns"].append({
                "table": name,
                "column": col_name,
                "risk": "Dangerous",
                "warning": "Column data will be permanently lost!",
            })
        
        # Modified columns
        for col_name in src_cols & tgt_cols:
            src_col = src_cols[col_name]
            tgt_col = tgt_cols[col_name]
            changes = []
            
            if src_col.data_type != tgt_col.data_type:
                changes.append(f"type: {src_col.data_type} -> {tgt_col.data_type}")
            if src_col.nullable != tgt_col.nullable:
                changes.append(f"nullable: {src_col.nullable} -> {tgt_col.nullable}")
            if src_col.default != tgt_col.default:
                changes.append(f"default: {src_col.default} -> {tgt_col.default}")
            
            if changes:
                diffs["modified_columns"].append({
                    "table": name,
                    "column": col_name,
                    "changes": changes,
                    "risk": "Dangerous" if "type" in str(changes) else "Caution",
                })
    
    # Risk summary
    risks = {"Safe": 0, "Caution": 0, "Dangerous": 0, "Breaking": 0}
    for category in ["new_tables", "dropped_tables", "new_columns", "dropped_columns", "modified_columns"]:
        for item in diffs[category]:
            risk = item.get("risk", "Safe")
            risks[risk] = risks.get(risk, 0) + 1
    
    diffs["risk_assessment"] = risks
    return diffs


def generate_migration_sql(diffs: dict, dialect: str = "postgresql") -> str:
    \"\"\"Generate UP migration SQL from diffs.\"\"\"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lines = [
        f"-- Migration: {timestamp}_auto_migration.sql",
        "-- Generated by AI Agent Toolkit - DB Migration Skill",
        "-- DO NOT EDIT MANUALLY",
        "",
        "-- UP MIGRATION --",
        "BEGIN;",
        "",
    ]
    
    # Create new tables
    for table in diffs["new_tables"]:
        lines.append(f"-- New table: {table['name']}")
        lines.append(f"-- CREATE TABLE {table['name']} (...); -- schema needs manual review")
        lines.append("")
    
    # Add new columns
    for col in diffs["new_columns"]:
        null_clause = "NOT NULL" if not col["nullable"] else ""
        default_clause = f"DEFAULT {col['default']}" if col.get("default") else ""
        lines.append(f"ALTER TABLE {col['table']} ADD COLUMN {col['column']} {col['type']} {null_clause} {default_clause};".strip())
    
    # Drop columns
    for col in diffs["dropped_columns"]:
        lines.append(f"-- WARNING: Destructive operation!")
        lines.append(f"-- ALTER TABLE {col['table']} DROP COLUMN {col['column']}; -- UNCOMMENT WITH CAUTION")
    
    lines.extend([
        "",
        "COMMIT;",
        "",
        "-- DOWN MIGRATION --",
        "BEGIN;",
        "",
    ])
    
    # DOWN: reverse of UP
    for col in reversed(diffs["new_columns"]):
        lines.append(f"-- ALTER TABLE {col['table']} DROP COLUMN IF EXISTS {col['column']};")
    
    for col in reversed(diffs["dropped_columns"]):
        lines.append(f"-- ALTER TABLE {col['table']} ADD COLUMN {col['column']} ...; -- needs original type")
    
    lines.extend([
        "",
        "COMMIT;",
    ])
    
    return "\n".join(lines)


def generate_report(diffs: dict, source_name: str, target_name: str) -> str:
    \"\"\"Generate a Markdown migration report.\"\"\"
    risks = diffs["risk_assessment"]
    total = sum(risks.values())
    
    lines = [
        "# Database Migration Report",
        "",
        f"**Source**: {source_name}",
        f"**Target**: {target_name}",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"## Summary: {total} changes detected",
        "",
        "| Risk Level | Count |",
        "|------------|-------|",
    ]
    for risk in ["Breaking", "Dangerous", "Caution", "Safe"]:
        if risks.get(risk, 0) > 0:
            lines.append(f"| {risk} | {risks[risk]} |")
    
    lines.append("")
    
    # New columns
    if diffs["new_columns"]:
        lines.append("## New Columns")
        lines.append("")
        for col in diffs["new_columns"]:
            lines.append(f"- `{col['table']}.{col['column']}` ({col['type']}) -- Risk: {col['risk']}")
        lines.append("")
    
    # Dropped columns
    if diffs["dropped_columns"]:
        lines.append("## Dropped Columns (DANGER)")
        lines.append("")
        for col in diffs["dropped_columns"]:
            lines.append(f"- `{col['table']}.{col['column']}` -- Data will be permanently lost!")
        lines.append("")
    
    # Modified columns
    if diffs["modified_columns"]:
        lines.append("## Modified Columns")
        lines.append("")
        for col in diffs["modified_columns"]:
            lines.append(f"- `{col['table']}.{col['column']}`: {', '.join(col['changes'])}")
        lines.append("")
    
    lines.extend([
        "---",
        "*Generated by AI Agent Toolkit - DB Migration Skill*",
    ])
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI Agent Toolkit - DB Migration")
    parser.add_argument("--source", help="Source database URL")
    parser.add_argument("--target", help="Target database URL")
    parser.add_argument("--source-file", help="Source schema SQL file")
    parser.add_argument("--target-file", help="Target schema SQL file")
    parser.add_argument("--orm", help="Path to ORM models directory")
    parser.add_argument("--dialect", default="postgresql", choices=["postgresql", "mysql", "sqlite"])
    parser.add_argument("--output", "-o", default="migration.sql", help="Output migration SQL file")
    parser.add_argument("--report", default="migration_report.md", help="Output report file")
    parser.add_argument("--apply", action="store_true", help="Apply the migration")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    parser.add_argument("--backup", action="store_true", help="Backup before applying")
    parser.add_argument("--rollback", action="store_true", help="Rollback last migration")
    parser.add_argument("--interactive", action="store_true", help="Confirm dangerous operations")

    args = parser.parse_args()

    if not args.source_file or not args.target_file:
        print("Error: --source-file and --target-file are required for SQL file comparison.")
        print("Example: python3 migrate.py --source-file old.sql --target-file new.sql")
        sys.exit(1)

    # Read schema files
    with open(args.source_file) as f:
        source_sql = f.read()
    with open(args.target_file) as f:
        target_sql = f.read()

    source_schema = parse_sql_schema(source_sql, args.dialect)
    target_schema = parse_sql_schema(target_sql, args.dialect)

    # Compare
    diffs = compare_schemas(source_schema, target_schema)
    
    # Generate report
    report = generate_report(diffs, args.source_file, args.target_file)
    with open(args.report, "w") as f:
        f.write(report)
    
    # Generate migration SQL
    migration_sql = generate_migration_sql(diffs, args.dialect)
    with open(args.output, "w") as f:
        f.write(migration_sql)
    
    # Print summary
    risks = diffs["risk_assessment"]
    total = sum(risks.values())
    print("=" * 50)
    print("Database Migration Report")
    print("=" * 50)
    print(f"Changes detected: {total}")
    for risk in ["Breaking", "Dangerous", "Caution", "Safe"]:
        if risks.get(risk, 0) > 0:
            print(f"  {risk}: {risks[risk]}")
    print(f"\nMigration SQL: {args.output}")
    print(f"Full report: {args.report}")
    
    if args.dry_run:
        print("\n--- DRY RUN - no changes applied ---")
        print(migration_sql[:2000])
    
    if args.apply:
        print("\nWARNING: --apply not implemented for SQL file mode.")
        print("Use the generated SQL file with your database client.")


if __name__ == "__main__":
    main()
