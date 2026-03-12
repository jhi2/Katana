#!/usr/bin/env python3
import os
import sys
import unittest


def main() -> int:
    repo_root = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(repo_root, "tests")

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=tests_dir, pattern="test*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
