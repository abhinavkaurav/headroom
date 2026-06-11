#!/usr/bin/env python3
"""Quick test utility for token compression on demand.

Usage:
    python test_compress.py                 # Run with example data
    python test_compress.py --model gpt-4o  # Specify model
    python test_compress.py --aggressive    # Compress aggressively
    python test_compress.py --input "your text here"

Examples:
    python test_compress.py
    python test_compress.py --model claude-opus-4-20250514 --target-ratio 0.5
    python test_compress.py --aggressive --compress-user-messages
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from headroom import compress, CompressConfig


SAMPLE_MESSAGES = [
    {
        "role": "user",
        "content": "Analyze this output from a build log and find errors"
    },
    {
        "role": "assistant",
        "content": "I'll help you analyze the build log. Please provide the full output and I'll identify any errors, warnings, or issues."
    },
    {
        "role": "user",
        "content": """
        [INFO] Scanning for projects...
        [INFO] ================================================================================
        [INFO] Building headroom 0.1.0
        [INFO] ================================================================================
        [INFO] --- maven-clean-plugin:3.1.0:clean (default-clean) @ headroom ---
        [INFO] Deleting /home/user/projects/headroom/target
        [INFO] --- maven-resources-plugin:3.2.0:resources (default-resources) @ headroom ---
        [INFO] Using 'UTF-8' encoding to copy filtered resources.
        [INFO] Copying 3 resources
        [INFO] --- maven-compiler-plugin:3.8.1:compile (default-compile) @ headroom ---
        [INFO] Changes detected - recompiling module
        [INFO] Compiling 45 source files to /home/user/projects/headroom/target/classes
        [WARNING] /home/user/projects/headroom/src/main/java/com/example/Service.java:[42,8] warning: unused variable
        [WARNING] /home/user/projects/headroom/src/main/java/com/example/Utils.java:[128,15] warning: raw use of parameterized class
        [INFO] --- maven-surefire-plugin:2.22.2:test (default-test) @ headroom ---
        [INFO] Running com.example.ServiceTest
        [INFO] Tests run: 45, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 2.345 s
        [INFO] Running com.example.UtilsTest
        [INFO] Tests run: 23, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 1.234 s
        [INFO] --- maven-jar-plugin:3.2.0:jar (default-jar) @ headroom ---
        [INFO] Building jar: /home/user/projects/headroom/target/headroom-0.1.0.jar
        [INFO] --- maven-shade-plugin:3.2.4:shade (default) @ headroom ---
        [INFO] Including org.apache.commons:commons-lang3:jar:3.12.0 in the shaded jar.
        [INFO] Including org.apache.commons:commons-io:jar:2.11.0 in the shaded jar.
        [INFO] Including com.google.guava:guava:jar:31.0.1-jre in the shaded jar.
        [INFO] Replacing original artifact with shaded artifact.
        [INFO] --- maven-install-plugin:2.8.1:install (default-install) @ headroom ---
        [INFO] Installing /home/user/projects/headroom/target/headroom-0.1.0.jar to /home/user/.m2/repository/com/example/headroom/0.1.0/headroom-0.1.0.jar
        [INFO] Installing /home/user/projects/headroom/pom.xml to /home/user/.m2/repository/com/example/headroom/0.1.0/headroom-0.1.0.pom
        [INFO] ================================================================================
        [INFO] BUILD SUCCESS
        [INFO] ================================================================================
        [INFO] Total time: 15.234 s
        [INFO] Finished at: 2025-06-04T14:35:22Z
        [INFO] Final Memory: 128M/512M
        """
    }
]


def format_ratio(ratio: float) -> str:
    """Format compression ratio as percentage."""
    return f"{ratio * 100:.1f}%"


def print_result(result, config_desc: str = ""):
    """Pretty print compression result."""
    print("\n" + "=" * 70)
    print("COMPRESSION RESULT" + (f" ({config_desc})" if config_desc else ""))
    print("=" * 70)
    print(f"Tokens Before:        {result.tokens_before:,}")
    print(f"Tokens After:         {result.tokens_after:,}")
    print(f"Tokens Saved:         {result.tokens_saved:,}")
    print(f"Compression Ratio:    {format_ratio(result.compression_ratio)} saved")
    if result.transforms_applied:
        print(f"Transforms Applied:   {', '.join(result.transforms_applied)}")
    print("=" * 70)
    if result.tokens_before > 0:
        efficiency = (result.tokens_saved / result.tokens_before) * 100
        print(f"Efficiency: Kept {format_ratio(1 - result.compression_ratio)}, "
              f"saved {efficiency:.1f}%")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Quick compression test utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6-20250514",
        help="Model to use for token counting (default: claude-sonnet-4-6-20250514)"
    )
    parser.add_argument(
        "--target-ratio",
        type=float,
        default=None,
        help="Target compression ratio (0.5 = keep 50%, None = aggressive)"
    )
    parser.add_argument(
        "--protect-recent",
        type=int,
        default=4,
        help="Don't compress last N messages (default: 4)"
    )
    parser.add_argument(
        "--compress-user-messages",
        action="store_true",
        help="Also compress user messages (default: False)"
    )
    parser.add_argument(
        "--compress-system-messages",
        action="store_true",
        default=True,
        help="Compress system messages (default: True)"
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Use aggressive compression (target_ratio=0.2, compress everything)"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Custom message content to test (replaces sample data)"
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Run with no optimization (baseline token count)"
    )

    args = parser.parse_args()

    # Build config
    config = CompressConfig()

    if args.aggressive:
        config.target_ratio = 0.2
        config.protect_recent = 1
        config.compress_user_messages = True
        desc = "aggressive (20% kept, no protection)"
    else:
        config.target_ratio = args.target_ratio
        config.protect_recent = args.protect_recent
        config.compress_user_messages = args.compress_user_messages
        config.compress_system_messages = args.compress_system_messages
        desc = f"conservative (target={args.target_ratio}, protect_recent={args.protect_recent})"

    # Build messages
    if args.input:
        messages = [
            {"role": "user", "content": args.input}
        ]
    else:
        messages = SAMPLE_MESSAGES

    # Run compression
    print(f"\nTesting compression with model: {args.model}")
    print(f"Configuration: {desc}")
    print(f"Input: {len(messages)} message(s)")

    if args.baseline:
        result = compress(messages, model=args.model, optimize=False)
        print_result(result, "BASELINE (no optimization)")
    else:
        result = compress(messages, model=args.model, config=config)
        print_result(result, desc)

    # Show sample of compressed output
    if result.tokens_saved > 0:
        print("First compressed message (truncated):")
        first_msg = result.messages[0]
        content = first_msg.get("content", "")[:200]
        print(f"   {content}...")


if __name__ == "__main__":
    main()
