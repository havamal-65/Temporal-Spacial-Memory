"""
Angular Sector System for Spatial Coordinate Computation

This module implements standardized angular categorization systems for the θ component
of the 4D polar-temporal coordinate system. It provides established number systems
for better organization and retrieval of spatial information.

Based on navigation standards from cartography and geospatial libraries like PROJ, GDAL.
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Union
from enum import Enum
from dataclasses import dataclass


class SectorSystem(Enum):
    """Available angular sector systems."""
    COMPASS_32 = "compass_32"
    COMPASS_16 = "compass_16" 
    COMPASS_8 = "compass_8"
    HEXADECIMAL_16 = "hex_16"
    OCTANTS_8 = "octants_8"
    QUADRANTS_4 = "quadrants_4"
    CONTINUOUS = "continuous"


@dataclass
class SectorInfo:
    """Information about an angular sector."""
    id: Union[str, int]
    name: str
    center_angle: float  # in radians
    start_angle: float   # in radians
    end_angle: float     # in radians
    width: float         # in radians
    system: SectorSystem


class AngularSectorSystem:
    """
    Manages angular sector systems for spatial coordinate computation.
    
    This class provides standardized angular categorization based on established
    navigation and coordinate reference systems used in cartography.
    """
    
    def __init__(self, system: SectorSystem = SectorSystem.COMPASS_32):
        """
        Initialize the angular sector system.
        
        Args:
            system: The sector system to use
        """
        self.system = system
        self.sectors = self._initialize_sectors()
        
    def _initialize_sectors(self) -> Dict[Union[str, int], SectorInfo]:
        """Initialize sector definitions based on selected system."""
        sectors = {}
        
        if self.system == SectorSystem.COMPASS_32:
            # 32-point compass rose (11.25° sectors)
            compass_names = [
                "N", "NbE", "NNE", "NEbN", "NE", "NEbE", "ENE", "EbN",
                "E", "EbS", "ESE", "SEbE", "SE", "SEbS", "SSE", "SbE",
                "S", "SbW", "SSW", "SWbS", "SW", "SWbW", "WSW", "WbS",
                "W", "WbN", "WNW", "NWbW", "NW", "NWbN", "NNW", "NbW"
            ]
            sector_width = 2 * np.pi / 32
            
            for i, name in enumerate(compass_names):
                center_angle = i * sector_width
                start_angle = (center_angle - sector_width/2) % (2 * np.pi)
                end_angle = (center_angle + sector_width/2) % (2 * np.pi)
                
                sectors[name] = SectorInfo(
                    id=name,
                    name=name,
                    center_angle=center_angle,
                    start_angle=start_angle,
                    end_angle=end_angle,
                    width=sector_width,
                    system=self.system
                )
                
        elif self.system == SectorSystem.COMPASS_16:
            # 16-point compass rose (22.5° sectors)
            compass_names = [
                "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
            ]
            sector_width = 2 * np.pi / 16
            
            for i, name in enumerate(compass_names):
                center_angle = i * sector_width
                start_angle = (center_angle - sector_width/2) % (2 * np.pi)
                end_angle = (center_angle + sector_width/2) % (2 * np.pi)
                
                sectors[name] = SectorInfo(
                    id=name,
                    name=name,
                    center_angle=center_angle,
                    start_angle=start_angle,
                    end_angle=end_angle,
                    width=sector_width,
                    system=self.system
                )
                
        elif self.system == SectorSystem.COMPASS_8:
            # 8-point compass rose (45° sectors)
            compass_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            sector_width = 2 * np.pi / 8
            
            for i, name in enumerate(compass_names):
                center_angle = i * sector_width
                start_angle = (center_angle - sector_width/2) % (2 * np.pi)
                end_angle = (center_angle + sector_width/2) % (2 * np.pi)
                
                sectors[name] = SectorInfo(
                    id=name,
                    name=name,
                    center_angle=center_angle,
                    start_angle=start_angle,
                    end_angle=end_angle,
                    width=sector_width,
                    system=self.system
                )
                
        elif self.system == SectorSystem.HEXADECIMAL_16:
            # Hexadecimal 16-sector system (22.5° sectors)
            hex_names = ['0', '1', '2', '3', '4', '5', '6', '7', 
                        '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']
            sector_width = 2 * np.pi / 16
            
            for i, name in enumerate(hex_names):
                center_angle = i * sector_width
                start_angle = (center_angle - sector_width/2) % (2 * np.pi)
                end_angle = (center_angle + sector_width/2) % (2 * np.pi)
                
                sectors[name] = SectorInfo(
                    id=name,
                    name=f"Sector_{name}",
                    center_angle=center_angle,
                    start_angle=start_angle,
                    end_angle=end_angle,
                    width=sector_width,
                    system=self.system
                )
                
        elif self.system == SectorSystem.OCTANTS_8:
            # Mathematical octant system
            octant_names = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
            sector_width = 2 * np.pi / 8
            
            for i, name in enumerate(octant_names):
                center_angle = i * sector_width
                start_angle = (center_angle - sector_width/2) % (2 * np.pi)
                end_angle = (center_angle + sector_width/2) % (2 * np.pi)
                
                sectors[name] = SectorInfo(
                    id=name,
                    name=f"Octant_{name}",
                    center_angle=center_angle,
                    start_angle=start_angle,
                    end_angle=end_angle,
                    width=sector_width,
                    system=self.system
                )
                
        elif self.system == SectorSystem.QUADRANTS_4:
            # Mathematical quadrant system
            quadrant_names = ["I", "II", "III", "IV"]
            sector_width = 2 * np.pi / 4
            
            for i, name in enumerate(quadrant_names):
                center_angle = i * sector_width
                start_angle = (center_angle - sector_width/2) % (2 * np.pi)
                end_angle = (center_angle + sector_width/2) % (2 * np.pi)
                
                sectors[name] = SectorInfo(
                    id=name,
                    name=f"Quadrant_{name}",
                    center_angle=center_angle,
                    start_angle=start_angle,
                    end_angle=end_angle,
                    width=sector_width,
                    system=self.system
                )
        
        return sectors
    
    def angle_to_sector(self, theta: float) -> SectorInfo:
        """
        Convert a continuous angle to its corresponding sector.
        
        Args:
            theta: Angle in radians [0, 2π)
            
        Returns:
            SectorInfo for the sector containing this angle
        """
        # Normalize theta to [0, 2π)
        theta = theta % (2 * np.pi)
        
        # Find the sector containing this angle
        for sector in self.sectors.values():
            if self._angle_in_sector(theta, sector):
                return sector
                
        # Fallback to first sector (shouldn't happen with proper normalization)
        return list(self.sectors.values())[0]
    
    def _angle_in_sector(self, theta: float, sector: SectorInfo) -> bool:
        """Check if an angle falls within a sector."""
        start = sector.start_angle
        end = sector.end_angle
        
        # Handle wrap-around case (sector crosses 0/2π boundary)
        if start > end:
            return theta >= start or theta <= end
        else:
            return start <= theta <= end
    
    def sector_to_angle(self, sector_id: Union[str, int]) -> float:
        """
        Get the center angle of a sector.
        
        Args:
            sector_id: Sector identifier
            
        Returns:
            Center angle of the sector in radians
        """
        if sector_id in self.sectors:
            return self.sectors[sector_id].center_angle
        else:
            raise ValueError(f"Unknown sector ID: {sector_id}")
    
    def quantize_angle(self, theta: float) -> float:
        """
        Quantize a continuous angle to its sector's center angle.
        
        Args:
            theta: Input angle in radians
            
        Returns:
            Quantized angle (sector center) in radians
        """
        sector = self.angle_to_sector(theta)
        return sector.center_angle
    
    def get_adjacent_sectors(self, sector_id: Union[str, int]) -> List[SectorInfo]:
        """
        Get the sectors adjacent to the given sector.
        
        Args:
            sector_id: Sector identifier
            
        Returns:
            List of adjacent sectors
        """
        if sector_id not in self.sectors:
            raise ValueError(f"Unknown sector ID: {sector_id}")
            
        sector_list = list(self.sectors.values())
        current_idx = None
        
        for i, sector in enumerate(sector_list):
            if sector.id == sector_id:
                current_idx = i
                break
                
        if current_idx is None:
            return []
            
        # Get previous and next sectors (with wrap-around)
        prev_idx = (current_idx - 1) % len(sector_list)
        next_idx = (current_idx + 1) % len(sector_list)
        
        return [sector_list[prev_idx], sector_list[next_idx]]
    
    def get_sector_range(self, center_sector_id: Union[str, int], 
                        radius: int = 1) -> List[SectorInfo]:
        """
        Get sectors within a given radius of a center sector.
        
        Args:
            center_sector_id: Center sector identifier
            radius: Number of sectors to include on each side
            
        Returns:
            List of sectors within the range
        """
        if center_sector_id not in self.sectors:
            raise ValueError(f"Unknown sector ID: {center_sector_id}")
            
        sector_list = list(self.sectors.values())
        current_idx = None
        
        for i, sector in enumerate(sector_list):
            if sector.id == center_sector_id:
                current_idx = i
                break
                
        if current_idx is None:
            return []
            
        result = []
        for offset in range(-radius, radius + 1):
            idx = (current_idx + offset) % len(sector_list)
            result.append(sector_list[idx])
            
        return result
    
    def get_sector_info(self, sector_id: Union[str, int]) -> Optional[SectorInfo]:
        """Get detailed information about a sector."""
        return self.sectors.get(sector_id)
    
    def list_all_sectors(self) -> List[SectorInfo]:
        """Get list of all sectors in the system."""
        return list(self.sectors.values())
    
    def get_system_info(self) -> Dict[str, Union[str, int, float]]:
        """Get information about the current sector system."""
        return {
            "system": self.system.value,
            "num_sectors": len(self.sectors),
            "sector_width_degrees": math.degrees(2 * np.pi / len(self.sectors)),
            "sector_width_radians": 2 * np.pi / len(self.sectors)
        }


# Convenience functions for common operations
def create_compass_32_system() -> AngularSectorSystem:
    """Create a 32-point compass sector system."""
    return AngularSectorSystem(SectorSystem.COMPASS_32)


def create_compass_16_system() -> AngularSectorSystem:
    """Create a 16-point compass sector system."""
    return AngularSectorSystem(SectorSystem.COMPASS_16)


def create_hex_system() -> AngularSectorSystem:
    """Create a hexadecimal 16-sector system."""
    return AngularSectorSystem(SectorSystem.HEXADECIMAL_16)


# Example usage and validation
if __name__ == "__main__":
    # Test the compass system
    compass = create_compass_32_system()
    
    # Test angle conversion
    test_angles = [0, np.pi/4, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi - 0.1]
    
    print("32-Point Compass System Test:")
    print("-" * 40)
    
    for angle in test_angles:
        sector = compass.angle_to_sector(angle)
        quantized = compass.quantize_angle(angle)
        
        print(f"Angle: {math.degrees(angle):6.1f}° → Sector: {sector.name:4s} "
              f"(Center: {math.degrees(sector.center_angle):6.1f}°)")
    
    print(f"\nSystem Info: {compass.get_system_info()}") 