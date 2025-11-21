"""
ODD Specification Schema

Defines the structure for Operational Design Domain specifications,
including numeric and categorical axes with boundaries and limits.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional
import json


@dataclass
class AxisSpecNumeric:
    """
    Numeric axis specification for ODD.
    
    Attributes:
        feature: Name of the feature (e.g., "speed", "roll_pitch")
        units: Unit of measurement (e.g., "m/s", "degrees")
        in_odd: [lower, upper] bounds for nominal ODD operation
        near_boundary: [lower, upper] bounds for near-boundary zone
        hard_limit: [lower, upper] absolute physical/safety limits
    """
    feature: str
    units: str
    in_odd: List[float]  # [L, U]
    near_boundary: List[float]  # [L_nb, U_nb]
    hard_limit: List[float]  # [L_h, U_h]
    
    def __post_init__(self):
        """Validate bounds are properly ordered."""
        if len(self.in_odd) != 2:
            raise ValueError(f"in_odd must have exactly 2 values, got {len(self.in_odd)}")
        if len(self.near_boundary) != 2:
            raise ValueError(f"near_boundary must have exactly 2 values, got {len(self.near_boundary)}")
        if len(self.hard_limit) != 2:
            raise ValueError(f"hard_limit must have exactly 2 values, got {len(self.hard_limit)}")
        
        # Verify ordering: in_odd ⊆ near_boundary ⊆ hard_limit
        if self.in_odd[0] < self.near_boundary[0] or self.in_odd[1] > self.near_boundary[1]:
            raise ValueError(f"in_odd {self.in_odd} must be within near_boundary {self.near_boundary}")
        if self.near_boundary[0] < self.hard_limit[0] or self.near_boundary[1] > self.hard_limit[1]:
            raise ValueError(f"near_boundary {self.near_boundary} must be within hard_limit {self.hard_limit}")
    
    def classify_value(self, value: float) -> str:
        """
        Classify a value as 'in_odd', 'near_boundary', or 'out_of_odd'.
        
        Args:
            value: The value to classify
            
        Returns:
            One of: 'in_odd', 'near_boundary', 'out_of_odd'
        """
        if self.in_odd[0] <= value <= self.in_odd[1]:
            return "in_odd"
        elif self.near_boundary[0] <= value <= self.near_boundary[1]:
            return "near_boundary"
        else:
            return "out_of_odd"
    
    def distance_from_odd(self, value: float) -> float:
        """
        Compute normalized distance from ODD center/bounds.
        
        Returns value in [0, 1] where:
        - 0 = at ODD center
        - ~0.3-0.5 = at ODD boundary
        - 1 = at hard limit
        
        Args:
            value: The value to measure
            
        Returns:
            Normalized distance in [0, 1]
        """
        odd_center = (self.in_odd[0] + self.in_odd[1]) / 2
        odd_radius = (self.in_odd[1] - self.in_odd[0]) / 2
        hard_range = self.hard_limit[1] - self.hard_limit[0]
        
        if hard_range == 0:
            return 0.0
        
        # Distance from center, normalized by hard range
        distance = abs(value - odd_center) / hard_range
        
        # If inside ODD, scale by proximity to boundary
        if self.in_odd[0] <= value <= self.in_odd[1]:
            if odd_radius > 0:
                return min(0.3, abs(value - odd_center) / odd_radius * 0.3)
            return 0.0
        
        # Outside ODD, scale from 0.3 to 1.0
        return min(1.0, 0.3 + distance * 0.7)


@dataclass
class AxisSpecCategorical:
    """
    Categorical axis specification for ODD.
    
    Attributes:
        feature: Name of the feature (e.g., "terrain", "lighting")
        allowed_in_odd: List of category values allowed in ODD
        allowed_all: Complete list of possible category values
    """
    feature: str
    allowed_in_odd: List[str]
    allowed_all: List[str]
    
    def __post_init__(self):
        """Validate that allowed_in_odd is a subset of allowed_all."""
        if not set(self.allowed_in_odd).issubset(set(self.allowed_all)):
            raise ValueError(
                f"allowed_in_odd {self.allowed_in_odd} must be a subset of "
                f"allowed_all {self.allowed_all}"
            )
    
    def classify_value(self, value: str) -> str:
        """
        Classify a categorical value.
        
        Args:
            value: The category value to classify
            
        Returns:
            One of: 'in_odd', 'out_of_odd', 'unknown'
        """
        if value in self.allowed_in_odd:
            return "in_odd"
        elif value in self.allowed_all:
            return "out_of_odd"
        else:
            return "unknown"


@dataclass
class OddSpec:
    """
    Complete ODD Specification.
    
    Attributes:
        version: Specification version string
        axes: Dictionary mapping axis names to axis specifications
        importance: Dictionary mapping axis names to importance weights
        description: Optional natural language description
    """
    version: str
    axes: Dict[str, Union[AxisSpecNumeric, AxisSpecCategorical]]
    importance: Dict[str, float]
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate that all axes have importance weights."""
        for axis_name in self.axes.keys():
            if axis_name not in self.importance:
                raise ValueError(f"Axis '{axis_name}' missing importance weight")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "version": self.version,
            "description": self.description,
            "axes": {},
            "importance": self.importance
        }
        
        for name, spec in self.axes.items():
            if isinstance(spec, AxisSpecNumeric):
                result["axes"][name] = {
                    "type": "numeric",
                    "feature": spec.feature,
                    "units": spec.units,
                    "in_odd": spec.in_odd,
                    "near_boundary": spec.near_boundary,
                    "hard_limit": spec.hard_limit
                }
            else:  # AxisSpecCategorical
                result["axes"][name] = {
                    "type": "categorical",
                    "feature": spec.feature,
                    "allowed_in_odd": spec.allowed_in_odd,
                    "allowed_all": spec.allowed_all
                }
        
        return result
    
    def to_json(self, filepath: Optional[str] = None) -> str:
        """
        Serialize to JSON.
        
        Args:
            filepath: Optional path to write JSON file
            
        Returns:
            JSON string
        """
        json_str = json.dumps(self.to_dict(), indent=2)
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
        return json_str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OddSpec':
        """Create OddSpec from dictionary."""
        axes = {}
        for name, spec_dict in data["axes"].items():
            if spec_dict["type"] == "numeric":
                axes[name] = AxisSpecNumeric(
                    feature=spec_dict["feature"],
                    units=spec_dict["units"],
                    in_odd=spec_dict["in_odd"],
                    near_boundary=spec_dict["near_boundary"],
                    hard_limit=spec_dict["hard_limit"]
                )
            else:  # categorical
                axes[name] = AxisSpecCategorical(
                    feature=spec_dict["feature"],
                    allowed_in_odd=spec_dict["allowed_in_odd"],
                    allowed_all=spec_dict["allowed_all"]
                )
        
        return cls(
            version=data["version"],
            axes=axes,
            importance=data["importance"],
            description=data.get("description")
        )
    
    @classmethod
    def from_json(cls, filepath: str) -> 'OddSpec':
        """Load OddSpec from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
