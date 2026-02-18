#!/usr/bin/env python3
"""
Test script to verify field validation enforcement in system prompt.
Tests that the LLM is properly instructed to validate fields before dashboard creation.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from apps.agent.mcp_agent import MCPAgent

def test_field_validation_prompt():
    """Test that field validation protocol is present in system prompt."""
    print("=" * 80)
    print("  TESTING FIELD VALIDATION PROTOCOL")
    print("=" * 80)
    print()
    
    agent = MCPAgent()
    
    # Generate system prompt
    system_prompt = agent._build_system_prompt(
        looker_url="https://test.looker.com",
        gcp_project="test-project",
        gcp_location="us-central1",
        explore_context=None
    )
    
    # Check for mandatory field verification
    checks = {
        "MANDATORY FIELD VERIFICATION": "MANDATORY FIELD VERIFICATION" in system_prompt,
        "STOP command": "⛔ STOP" in system_prompt,
        "POC Mode instruction": "POC Mode" in system_prompt,
        "Production Mode instruction": "Production Mode" in system_prompt,
        "Verification checklist": "✅" in system_prompt and "verified in explore" in system_prompt,
        "Forbidden field invention": "❌ FORBIDDEN: Inventing fields" in system_prompt,
        "Tool will fail warning": "IF YOU SKIP VERIFICATION, THE TOOL WILL FAIL" in system_prompt,
    }
    
    print("📋 Field Validation Protocol Checks:")
    print()
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {check_name}")
        if not passed:
            all_passed = False
    
    print()
    
    # Extract and display the field validation section
    if "MANDATORY FIELD VERIFICATION" in system_prompt:
        start_idx = system_prompt.find("MANDATORY FIELD VERIFICATION")
        end_idx = system_prompt.find("VISUALIZATION TYPE CONFIGURATION", start_idx)
        if end_idx == -1:
            end_idx = start_idx + 1000
        
        validation_section = system_prompt[start_idx:end_idx]
        print("📄 Field Validation Section:")
        print("-" * 80)
        print(validation_section[:500] + "..." if len(validation_section) > 500 else validation_section)
        print("-" * 80)
        print()
    
    if all_passed:
        print("✅ ALL FIELD VALIDATION CHECKS PASSED!")
        return True
    else:
        print("❌ SOME FIELD VALIDATION CHECKS FAILED!")
        return False

def test_viz_type_configuration():
    """Test that visualization type configuration is present in system prompt."""
    print()
    print("=" * 80)
    print("  TESTING VISUALIZATION TYPE CONFIGURATION")
    print("=" * 80)
    print()
    
    agent = MCPAgent()
    
    # Generate system prompt
    system_prompt = agent._build_system_prompt(
        looker_url="https://test.looker.com",
        gcp_project="test-project",
        gcp_location="us-central1",
        explore_context=None
    )
    
    # Check for viz type configuration
    viz_types = [
        ("looker_line", "Time series, trends"),
        ("looker_column", "Comparisons, categories"),
        ("looker_bar", "Rankings, horizontal"),
        ("looker_pie", "Part-to-whole"),
        ("looker_grid", "Tables, detailed data"),
        ("looker_single_value", "KPIs, single metrics"),
    ]
    
    checks = {
        "Viz type section": "VISUALIZATION TYPE CONFIGURATION" in system_prompt,
        "MAX 7 slices for pie": "MAX 7 slices" in system_prompt,
        "Single value config": "ONLY 1 measure, NO dimensions" in system_prompt,
    }
    
    print("📋 Visualization Type Configuration Checks:")
    print()
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {check_name}")
        if not passed:
            all_passed = False
    
    print()
    print("📊 Viz Types Documented:")
    print()
    
    for viz_type, description in viz_types:
        present = viz_type in system_prompt and description in system_prompt
        status = "✅" if present else "❌"
        print(f"   {status} {viz_type}: {description}")
        if not present:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✅ ALL VIZ TYPE CHECKS PASSED!")
        return True
    else:
        print("❌ SOME VIZ TYPE CHECKS FAILED!")
        return False

def test_insights_structure():
    """Test that insights structure is enforced in system prompt."""
    print()
    print("=" * 80)
    print("  TESTING INSIGHTS STRUCTURE ENFORCEMENT")
    print("=" * 80)
    print()
    
    agent = MCPAgent()
    
    # Generate system prompt
    system_prompt = agent._build_system_prompt(
        looker_url="https://test.looker.com",
        gcp_project="test-project",
        gcp_location="us-central1",
        explore_context=None
    )
    
    # Check for insights structure
    checks = {
        "Insights format section": "INSIGHTS FORMAT" in system_prompt,
        "MANDATORY requirement": "MANDATORY - ALL 4 SECTIONS REQUIRED" in system_prompt,
        "INSIGHTS section": "🔎 INSIGHTS (What happened?)" in system_prompt,
        "TRENDS section": "📊 TRENDS (Why did it happen?)" in system_prompt,
        "RECOMMENDATIONS section": "🎯 RECOMMENDATIONS (What should we do?)" in system_prompt,
        "FOLLOW-UP QUESTIONS section": "❓ FOLLOW-UP QUESTIONS (What should we explore next?)" in system_prompt,
        "Forbidden chart descriptions": "❌ FORBIDDEN: Chart descriptions without analysis" in system_prompt,
        "Forbidden missing sections": "❌ FORBIDDEN: Missing any of the 4 sections" in system_prompt,
        "Required quantified impact": "✅ REQUIRED: Business insights with quantified impact" in system_prompt,
    }
    
    print("📋 Insights Structure Checks:")
    print()
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {check_name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✅ ALL INSIGHTS STRUCTURE CHECKS PASSED!")
        return True
    else:
        print("❌ SOME INSIGHTS STRUCTURE CHECKS FAILED!")
        return False

def test_token_limit():
    """Test that token limit has been increased."""
    print()
    print("=" * 80)
    print("  TESTING TOKEN LIMIT INCREASE")
    print("=" * 80)
    print()
    
    # Read the mcp_agent.py file to check max_tokens value
    agent_file = os.path.join(os.path.dirname(__file__), '..', 'apps', 'agent', 'mcp_agent.py')
    
    with open(agent_file, 'r') as f:
        content = f.read()
    
    # Find max_tokens setting
    import re
    matches = re.findall(r'max_tokens\s*=\s*(\d+)', content)
    
    print("📋 Token Limit Checks:")
    print()
    
    if matches:
        max_token_value = int(matches[0])
        print(f"   Found max_tokens = {max_token_value}")
        print()
        
        if max_token_value >= 30000:
            print(f"   ✅ PASS: Token limit is {max_token_value} (>= 30,000)")
            print()
            print("✅ TOKEN LIMIT CHECK PASSED!")
            return True
        else:
            print(f"   ❌ FAIL: Token limit is {max_token_value} (< 30,000)")
            print()
            print("❌ TOKEN LIMIT CHECK FAILED!")
            return False
    else:
        print("   ❌ FAIL: Could not find max_tokens setting")
        print()
        print("❌ TOKEN LIMIT CHECK FAILED!")
        return False

if __name__ == "__main__":
    print()
    print("🧪 RUNNING QUALITY IMPROVEMENTS TESTS")
    print()
    
    results = []
    
    # Run all tests
    results.append(("Field Validation", test_field_validation_prompt()))
    results.append(("Viz Type Configuration", test_viz_type_configuration()))
    results.append(("Insights Structure", test_insights_structure()))
    results.append(("Token Limit", test_token_limit()))
    
    # Summary
    print()
    print("=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print()
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        sys.exit(1)
