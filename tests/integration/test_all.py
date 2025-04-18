"""
Test suite for all integration tests.

This module collects all integration tests into a single test suite.
"""

import unittest

from tests.integration.test_end_to_end import EndToEndTest
from tests.integration.test_workflows import WorkflowTest


def load_tests(loader, standard_tests, pattern):
    """Load all integration tests into a test suite."""
    suite = unittest.TestSuite()
    
    # Add end-to-end tests
    suite.addTests(loader.loadTestsFromTestCase(EndToEndTest))
    
    # Add workflow tests
    suite.addTests(loader.loadTestsFromTestCase(WorkflowTest))
    
    return suite


if __name__ == '__main__':
    unittest.main() 