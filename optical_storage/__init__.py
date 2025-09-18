"""
5D Optical Storage System by Aionix Data

A comprehensive storage system with advanced encryption and data integrity features.
"""

__version__ = "1.0.0"
__author__ = "Aionix Data"

from .core import OpticalStorage
from .security import SecurityManager
from .storage import ObjectStore

__all__ = ['OpticalStorage', 'SecurityManager', 'ObjectStore']