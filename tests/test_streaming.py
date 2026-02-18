#!/usr/bin/env python3
"""
Test script to verify streaming API implementation and timeout configuration.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from apps.agent.mcp_agent import MCPAgent
import httpx

def test_timeout_configuration():
    """Test that Anthropic client is configured with extended timeouts."""
    print("=" * 80)
    print("  TESTING TIMEOUT CONFIGURATION")
    print("=" * 80)
    print()
    
    agent = MCPAgent(model_name="claude-sonnet-4-20250514")
    
    # Check if client has timeout configuration
    if hasattr(agent, 'client') and hasattr(agent.client, '_client'):
        timeout = agent.client._client.timeout
        
        print("📋 Timeout Configuration:")
        print()
        
        if isinstance(timeout, httpx.Timeout):
            print(f"   ✅ Connect timeout: {timeout.connect}s")
            print(f"   ✅ Read timeout: {timeout.read}s (should be 600s)")
            print(f"   ✅ Write timeout: {timeout.write}s")
            print(f"   ✅ Pool timeout: {timeout.pool}s")
            print()
            
            if timeout.read >= 600.0:
                print("✅ TIMEOUT CONFIGURATION PASSED!")
                return True
            else:
                print(f"❌ Read timeout is {timeout.read}s, expected >= 600s")
                return False
        else:
            print(f"   ❌ Timeout is not httpx.Timeout: {type(timeout)}")
            return False
    else:
        print("   ❌ Could not access client timeout configuration")
        return False

def test_max_tokens():
    """Test that max_tokens has been reduced to 20K."""
    print()
    print("=" * 80)
    print("  TESTING MAX_TOKENS CONFIGURATION")
    print("=" * 80)
    print()
    
    # Read the mcp_agent.py file to check max_tokens value
    agent_file = os.path.join(os.path.dirname(__file__), '..', 'apps', 'agent', 'mcp_agent.py')
    
    with open(agent_file, 'r') as f:
        content = f.read()
    
    # Find max_tokens setting in streaming context
    import re
    # Look for max_tokens in the streaming API call
    matches = re.findall(r'max_tokens\s*=\s*(\d+)', content)
    
    print("📋 Max Tokens Configuration:")
    print()
    
    if matches:
        max_token_value = int(matches[0])
        print(f"   Found max_tokens = {max_token_value}")
        print()
        
        if max_token_value == 20000:
            print(f"   ✅ PASS: Token limit is {max_token_value} (expected 20,000)")
            print()
            print("✅ MAX_TOKENS CHECK PASSED!")
            return True
        else:
            print(f"   ⚠️  Token limit is {max_token_value}, expected 20,000")
            print()
            if max_token_value < 20000:
                print("❌ MAX_TOKENS CHECK FAILED (too low)!")
            else:
                print("⚠️  MAX_TOKENS is higher than recommended")
            return max_token_value == 20000
    else:
        print("   ❌ FAIL: Could not find max_tokens setting")
        print()
        print("❌ MAX_TOKENS CHECK FAILED!")
        return False

def test_streaming_api():
    """Test that streaming API is being used."""
    print()
    print("=" * 80)
    print("  TESTING STREAMING API IMPLEMENTATION")
    print("=" * 80)
    print()
    
    # Read the mcp_agent.py file to check for streaming API usage
    agent_file = os.path.join(os.path.dirname(__file__), '..', 'apps', 'agent', 'mcp_agent.py')
    
    with open(agent_file, 'r') as f:
        content = f.read()
    
    checks = {
        "messages.stream() usage": "messages.stream(" in content,
        "text_stream iteration": "text_stream" in content,
        "get_final_message() call": "get_final_message()" in content,
        "async with stream": "async with" in content and "stream" in content,
    }
    
    print("📋 Streaming API Checks:")
    print()
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {check_name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✅ ALL STREAMING API CHECKS PASSED!")
        return True
    else:
        print("❌ SOME STREAMING API CHECKS FAILED!")
        return False

if __name__ == "__main__":
    print()
    print("🧪 RUNNING STREAMING & TIMEOUT TESTS")
    print()
    
    results = []
    
    # Run all tests
    results.append(("Timeout Configuration", test_timeout_configuration()))
    results.append(("Max Tokens", test_max_tokens()))
    results.append(("Streaming API", test_streaming_api()))
    
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
