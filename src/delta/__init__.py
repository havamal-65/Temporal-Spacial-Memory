"""
Delta chain system for the Temporal-Spatial Knowledge Database.

This module provides a complete delta chain system for tracking
the evolution of node content over time with space-efficient storage.
"""

from .operations import (
    DeltaOperation,
    SetValueOperation,
    DeleteValueOperation,
    ArrayInsertOperation,
    ArrayDeleteOperation,
    TextDiffOperation,
    CompositeOperation
)

from .records import DeltaRecord
from .chain import DeltaChain
from .store import DeltaStore, RocksDBDeltaStore
from .reconstruction import StateReconstructor
from .detector import ChangeDetector
from .navigator import TimeNavigator
from .optimizer import ChainOptimizer

__all__ = [
    # Operations
    'DeltaOperation',
    'SetValueOperation',
    'DeleteValueOperation',
    'ArrayInsertOperation',
    'ArrayDeleteOperation',
    'TextDiffOperation',
    'CompositeOperation',
    
    # Core classes
    'DeltaRecord',
    'DeltaChain',
    'DeltaStore',
    'RocksDBDeltaStore',
    
    # Utility classes
    'StateReconstructor',
    'ChangeDetector',
    'TimeNavigator',
    'ChainOptimizer'
] 