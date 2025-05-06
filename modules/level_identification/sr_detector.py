# modules/level_identification/sr_detector.py
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.interfaces import IModule
from core.models import PriceData, PriceLevel, LevelData

class SupportResistanceDetector(IModule):
    """Identifies support and resistance levels from price data."""
    
    def __init__(self, module_id: Optional[str] = "sr_detector"):
        super().__init__(module_id=module_id)
        self.window_size = 10
        self.threshold = 0.03  # 3% threshold for level detection
        self.min_strength = 0.5
        self.max_levels = 5
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the detector.
        
        Args:
            config: Configuration dictionary with the following options:
                - window_size: Window size for peak detection
                - threshold: Percentage threshold for level detection
                - min_strength: Minimum strength for a level to be considered valid
                - max_levels: Maximum number of levels to return
        """
        self.window_size = config.get("window_size", 10)
        self.threshold = config.get("threshold", 0.03)
        self.min_strength = config.get("min_strength", 0.5)
        self.max_levels = config.get("max_levels", 5)
        super().configure(config)
    
    def execute(self, input_data: PriceData) -> LevelData:
        """Detect support and resistance levels from price data.
        
        Args:
            input_data: PriceData object
            
        Returns:
            LevelData object containing detected levels
        """
        df = input_data.to_dataframe()
        if len(df) < self.window_size * 2:
            return LevelData(
                symbol=input_data.symbol,
                timeframe=input_data.timeframe,
                levels=[],
                last_updated=datetime.now()
            )
        
        # Find peaks and troughs
        highs = df['high'].values
        lows = df['low'].values
        
        resistance_levels = self._find_peaks(highs)
        support_levels = self._find_troughs(lows)
        
        # Create PriceLevel objects
        levels = []
        
        for price, strength in resistance_levels:
            if strength >= self.min_strength:
                level = PriceLevel(
                    price=price,
                    level_type="resistance",
                    strength=strength,
                    created_at=datetime.now()
                )
                levels.append(level)
        
        for price, strength in support_levels:
            if strength >= self.min_strength:
                level = PriceLevel(
                    price=price,
                    level_type="support",
                    strength=strength,
                    created_at=datetime.now()
                )
                levels.append(level)
        
        # Sort by strength and limit number of levels
        levels.sort(key=lambda x: x.strength, reverse=True)
        levels = levels[:self.max_levels]
        
        return LevelData(
            symbol=input_data.symbol,
            timeframe=input_data.timeframe,
            levels=levels,
            last_updated=datetime.now()
        )
    
    def _find_peaks(self, data: np.ndarray) -> List[Tuple[float, float]]:
        """Find peaks in the data (resistance levels)."""
        peaks = []
        window = self.window_size
        
        for i in range(window, len(data) - window):
            # Check if current point is a peak
            if data[i] == max(data[i-window:i+window+1]):
                # Calculate strength based on how much higher the peak is
                left_diff = (data[i] - min(data[i-window:i])) / data[i]
                right_diff = (data[i] - min(data[i+1:i+window+1])) / data[i]
                strength = min(left_diff, right_diff) / self.threshold
                
                if strength > 0:
                    strength = min(strength, 1.0)  # Cap at 1.0
                    peaks.append((data[i], strength))
        
        # Cluster similar price levels
        clustered_peaks = self._cluster_levels(peaks)
        return clustered_peaks
    
    def _find_troughs(self, data: np.ndarray) -> List[Tuple[float, float]]:
        """Find troughs in the data (support levels)."""
        troughs = []
        window = self.window_size
        
        for i in range(window, len(data) - window):
            # Check if current point is a trough
            if data[i] == min(data[i-window:i+window+1]):
                # Calculate strength based on how much lower the trough is
                left_diff = (max(data[i-window:i]) - data[i]) / data[i]
                right_diff = (max(data[i+1:i+window+1]) - data[i]) / data[i]
                strength = min(left_diff, right_diff) / self.threshold
                
                if strength > 0:
                    strength = min(strength, 1.0)  # Cap at 1.0
                    troughs.append((data[i], strength))
        
        # Cluster similar price levels
        clustered_troughs = self._cluster_levels(troughs)
        return clustered_troughs
    
    def _cluster_levels(self, levels: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Cluster similar price levels and merge them."""
        if not levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x[0])
        
        clustered = []
        current_cluster = [sorted_levels[0]]
        
        for i in range(1, len(sorted_levels)):
            current_price, current_strength = sorted_levels[i]
            prev_price, _ = sorted_levels[i-1]
            
            # If prices are close enough, add to cluster
            if abs(current_price - prev_price) / prev_price < self.threshold / 2:
                current_cluster.append(sorted_levels[i])
            else:
                # Process the current cluster
                if current_cluster:
                    avg_price = sum(p for p, _ in current_cluster) / len(current_cluster)
                    avg_strength = sum(s for _, s in current_cluster) / len(current_cluster)
                    clustered.append((avg_price, avg_strength))
                
                # Start a new cluster
                current_cluster = [sorted_levels[i]]
        
        # Process the final cluster
        if current_cluster:
            avg_price = sum(p for p, _ in current_cluster) / len(current_cluster)
            avg_strength = sum(s for _, s in current_cluster) / len(current_cluster)
            clustered.append((avg_price, avg_strength))
        
        return clustered