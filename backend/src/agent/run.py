#!/usr/bin/env python3
"""
CLI entry point for the multichannel agent.
"""

import os
import sys
import argparse
from typing import Optional

from .graph import run_workflow, run_workflow_interactive
from .state import create_initial_state


def main():
    """
    Main CLI entry point.
    """
    parser = argparse.ArgumentParser(
        description="Multichannel Agent - Send emails and post to LinkedIn",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.agent.run "Send email to john@example.com about project update"
  python -m src.agent.run "Post on LinkedIn about our new product launch"
  python -m src.agent.run --interactive "Send email to team@company.com"
  python -m src.agent.run --thread-id "session-123" "Post LinkedIn update"
        """
    )
    
    parser.add_argument(
        "prompt",
        help="User prompt describing what to send/post"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode with human-in-the-loop"
    )
    
    parser.add_argument(
        "--thread-id",
        default="default",
        help="Thread ID for workflow state (default: 'default')"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Check MCP server availability
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-c", "import src.mcp.channels.server"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("⚠️  Warning: MCP server may not be available")
            if args.verbose:
                print(f"MCP server check failed: {result.stderr}")
    except Exception as e:
        print(f"⚠️  Warning: Could not check MCP server: {e}")
    
    # Run workflow
    print(f"🤖 Multichannel Agent")
    print(f"📝 Prompt: {args.prompt}")
    print(f"🔄 Mode: {'Interactive' if args.interactive else 'Standard'}")
    print(f"🧵 Thread ID: {args.thread_id}")
    print("=" * 50)
    
    try:
        if args.interactive:
            result = run_workflow_interactive(args.prompt, args.thread_id)
        else:
            result = run_workflow(args.prompt, args.thread_id)
        
        # Display results
        print("\n📊 Workflow Results:")
        print("=" * 30)
        
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
            sys.exit(1)
        
        if result.get("result"):
            result_data = result["result"]
            if result_data.get("status") == "success":
                print(f"✅ Success: {result_data.get('message', 'Operation completed')}")
            else:
                print(f"❌ Failed: {result_data.get('message', 'Unknown error')}")
                sys.exit(1)
        
        if args.verbose:
            print(f"\n🔍 Final State:")
            for key, value in result.items():
                if key not in ["result", "error"]:
                    print(f"  {key}: {value}")
        
        print("\n🎉 Workflow completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Workflow interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_simple_test():
    """
    Run a simple test without CLI arguments.
    """
    print("🧪 Running Simple Test")
    print("=" * 30)
    
    # Test email
    test_prompt = "Send email to test@example.com about project update"
    print(f"Test: {test_prompt}")
    
    try:
        result = run_workflow(test_prompt, "test-thread")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments provided, run simple test
        run_simple_test()
    else:
        # Run with CLI arguments
        main()
