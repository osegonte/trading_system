# modules/strategies/research/cluster_momentum.py
import numpy as np
import pandas as pd
import pandas_ta as ta
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy import stats
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta

from core.interfaces import IModule
from core.models import SignalData, SignalType

class ClusterMomentumStrategy(IModule):
    """
    Research-grade cluster-momentum strategy using RSI-anchored K-means clustering.
    Holding period: 1-4 weeks, rebalanced monthly.
    """
    
    def __init__(self, module_id: Optional[str] = "cluster_momentum"):
        super().__init__(module_id=module_id)
        self.logger = logging.getLogger("ClusterMomentumStrategy")
        
        # Strategy parameters
        self.lookback_years = 4
        self.n_clusters = 4
        self.target_rsi_levels = [30, 45, 55, 70]
        self.rebalance_day = 1  # First trading day of month
        self.min_permutation_pvalue = 0.01
        
        # Model components
        self.scaler = StandardScaler()
        self.kmeans = None
        self.feature_columns = []
        
        # Performance tracking
        self.last_rebalance = None
        self.current_cluster_weights = {}
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure cluster momentum strategy."""
        self.lookback_years = config.get("lookback_years", 4)
        self.n_clusters = config.get("n_clusters", 4)
        self.min_permutation_pvalue = config.get("min_permutation_pvalue", 0.01)
        super().configure(config)
        
    def execute(self, input_data: Dict[str, Any]) -> List[SignalData]:
        """Execute cluster momentum strategy."""
        price_data = input_data.get("price_data", {})
        current_date = input_data.get("current_date", datetime.now())
        
        # Check if rebalancing is needed
        if not self._should_rebalance(current_date):
            return []
        
        try:
            # Build feature matrix for all symbols
            feature_matrix, symbols = self._build_feature_matrix(price_data)
            
            if feature_matrix is None or len(feature_matrix) < 50:
                self.logger.warning("Insufficient data for clustering")
                return []
            
            # Perform clustering
            clusters = self._perform_clustering(feature_matrix)
            
            # Validate clustering with permutation test
            if not self._validate_clustering(feature_matrix, clusters):
                self.logger.warning("Clustering failed permutation test")
                return []
            
            # Select target cluster (RSI ~70 - momentum cluster)
            target_cluster = self._select_target_cluster(feature_matrix, clusters)
            
            # Optimize portfolio weights for target cluster
            cluster_weights = self._optimize_portfolio_weights(
                feature_matrix, clusters, target_cluster, symbols
            )
            
            # Generate rebalancing signals
            signals = self._generate_rebalancing_signals(cluster_weights, price_data)
            
            # Update state
            self.current_cluster_weights = cluster_weights
            self.last_rebalance = current_date
            
            self.logger.info(f"Generated {len(signals)} cluster momentum signals")
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in cluster momentum execution: {e}")
            return []
    
    def _should_rebalance(self, current_date: datetime) -> bool:
        """Check if monthly rebalancing is needed."""
        if self.last_rebalance is None:
            return True
        
        # Rebalance on first trading day of each month
        if (current_date.day == self.rebalance_day and 
            current_date.month != self.last_rebalance.month):
            return True
        
        return False
    
    def _build_feature_matrix(self, price_data: Dict) -> Tuple[Optional[np.ndarray], List[str]]:
        """Build feature matrix with 18 technical indicators."""
        features_list = []
        symbols = []
        
        for symbol, data in price_data.items():
            if not data.bars or len(data.bars) < 252:  # Need at least 1 year
                continue
                
            try:
                # Convert to DataFrame
                df = data.to_dataframe()
                
                # Calculate features
                features = self._calculate_features(df)
                
                if features is not None and not features.isna().any():
                    features_list.append(features.values)
                    symbols.append(symbol)
                    
            except Exception as e:
                self.logger.warning(f"Error calculating features for {symbol}: {e}")
                continue
        
        if not features_list:
            return None, []
        
        feature_matrix = np.array(features_list)
        return feature_matrix, symbols
    
    def _calculate_features(self, df: pd.DataFrame) -> Optional[pd.Series]:
        """Calculate 18 technical indicators for clustering."""
        try:
            # Price-based indicators
            rsi = ta.rsi(df['close'], length=14).iloc[-1]
            bb_percent = ta.bbands(df['close'], length=20)['BBP_20_2.0'].iloc[-1]
            
            # Momentum indicators
            mom_1m = ((df['close'].iloc[-1] / df['close'].iloc[-21]) - 1) * 100  # 1-month momentum
            mom_3m = ((df['close'].iloc[-1] / df['close'].iloc[-63]) - 1) * 100  # 3-month momentum
            mom_6m = ((df['close'].iloc[-1] / df['close'].iloc[-126]) - 1) * 100  # 6-month momentum
            mom_12m = ((df['close'].iloc[-1] / df['close'].iloc[-252]) - 1) * 100  # 12-month momentum
            
            # Volatility indicators
            atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
            atr_ratio = atr / df['close'].iloc[-1] * 100
            
            # Volume indicators
            volume_sma = df['volume'].rolling(20).mean().iloc[-1]
            volume_ratio = df['volume'].iloc[-1] / volume_sma if volume_sma > 0 else 1
            
            # Trend indicators
            ema_12 = ta.ema(df['close'], length=12).iloc[-1]
            ema_26 = ta.ema(df['close'], length=26).iloc[-1]
            macd_signal = (ema_12 - ema_26) / df['close'].iloc[-1] * 100
            
            # Support/Resistance strength
            high_52w = df['high'].rolling(252).max().iloc[-1]
            low_52w = df['low'].rolling(252).min().iloc[-1]
            price_position = (df['close'].iloc[-1] - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0.5
            
            # Additional momentum features
            roc_10 = ta.roc(df['close'], length=10).iloc[-1]
            stoch_k = ta.stoch(df['high'], df['low'], df['close'])['STOCHk_14_3_3'].iloc[-1]
            
            # Market regime indicators
            sma_50 = ta.sma(df['close'], length=50).iloc[-1]
            sma_200 = ta.sma(df['close'], length=200).iloc[-1]
            regime_indicator = (sma_50 / sma_200 - 1) * 100
            
            # Sector beta (simplified using market correlation)
            returns = df['close'].pct_change().dropna()
            market_beta = 1.0  # Would calculate vs SPY in production
            
            # Combine all features
            features = pd.Series({
                'rsi': rsi,
                'bb_percent': bb_percent,
                'momentum_1m': mom_1m,
                'momentum_3m': mom_3m,
                'momentum_6m': mom_6m,
                'momentum_12m': mom_12m,
                'atr_ratio': atr_ratio,
                'volume_ratio': volume_ratio,
                'macd_signal': macd_signal,
                'price_position_52w': price_position,
                'roc_10': roc_10,
                'stoch_k': stoch_k,
                'regime_indicator': regime_indicator,
                'market_beta': market_beta,
                'volatility_rank': self._calculate_volatility_rank(df),
                'mean_reversion': self._calculate_mean_reversion_score(df),
                'breakout_strength': self._calculate_breakout_strength(df),
                'liquidity_score': self._calculate_liquidity_score(df)
            })
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error calculating features: {e}")
            return None
    
    def _calculate_volatility_rank(self, df: pd.DataFrame) -> float:
        """Calculate volatility percentile rank."""
        returns = df['close'].pct_change().dropna()
        current_vol = returns.rolling(20).std().iloc[-1]
        vol_series = returns.rolling(20).std().dropna()
        return stats.percentileofscore(vol_series, current_vol) / 100
    
    def _calculate_mean_reversion_score(self, df: pd.DataFrame) -> float:
        """Calculate mean reversion tendency."""
        returns = df['close'].pct_change().dropna()
        # Hurst exponent approximation
        lags = range(2, 100)
        tau = [np.sqrt(np.std(np.subtract(returns[lag:], returns[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0  # Hurst exponent
    
    def _calculate_breakout_strength(self, df: pd.DataFrame) -> float:
        """Calculate breakout strength based on recent price action."""
        high_20 = df['high'].rolling(20).max().iloc[-1]
        low_20 = df['low'].rolling(20).min().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        if current_price >= high_20:
            return 1.0  # Strong bullish breakout
        elif current_price <= low_20:
            return -1.0  # Strong bearish breakout
        else:
            # Position within range
            return (current_price - low_20) / (high_20 - low_20) * 2 - 1
    
    def _calculate_liquidity_score(self, df: pd.DataFrame) -> float:
        """Calculate liquidity score based on volume patterns."""
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        avg_dollar_volume = (df['close'] * df['volume']).rolling(20).mean().iloc[-1]
        
        # Normalize by typical values (would use market benchmarks in production)
        volume_score = min(avg_volume / 1000000, 1.0)  # Cap at 1M shares
        dollar_score = min(avg_dollar_volume / 10000000, 1.0)  # Cap at 10M dollars
        
        return (volume_score + dollar_score) / 2
    
    def _perform_clustering(self, feature_matrix: np.ndarray) -> np.ndarray:
        """Perform K-means clustering with RSI anchoring."""
        # Standardize features
        scaled_features = self.scaler.fit_transform(feature_matrix)
        
        # Initialize centroids with RSI anchoring
        rsi_column = 0  # RSI is first feature
        initial_centroids = self._initialize_rsi_anchored_centroids(scaled_features, rsi_column)
        
        # Perform clustering
        self.kmeans = KMeans(
            n_clusters=self.n_clusters,
            init=initial_centroids,
            n_init=10,
            max_iter=300,
            random_state=42
        )
        
        clusters = self.kmeans.fit_predict(scaled_features)
        return clusters
    
    def _initialize_rsi_anchored_centroids(self, features: np.ndarray, rsi_column: int) -> np.ndarray:
        """Initialize cluster centroids anchored at target RSI levels."""
        centroids = np.zeros((self.n_clusters, features.shape[1]))
        
        # Sort features by RSI
        rsi_values = features[:, rsi_column]
        sorted_indices = np.argsort(rsi_values)
        
        # Assign centroids based on RSI quantiles
        for i in range(self.n_clusters):
            quantile = (i + 1) / (self.n_clusters + 1)
            quantile_idx = int(quantile * len(sorted_indices))
            centroid_idx = sorted_indices[quantile_idx]
            centroids[i] = features[centroid_idx]
        
        return centroids
    
    def _validate_clustering(self, features: np.ndarray, clusters: np.ndarray) -> bool:
        """Validate clustering using permutation test."""
        try:
            # Calculate actual within-cluster sum of squares
            actual_wcss = self._calculate_wcss(features, clusters)
            
            # Perform permutation test
            n_permutations = 1000
            permutation_wcss = []
            
            for _ in range(n_permutations):
                # Randomly permute cluster assignments
                perm_clusters = np.random.permutation(clusters)
                perm_wcss = self._calculate_wcss(features, perm_clusters)
                permutation_wcss.append(perm_wcss)
            
            # Calculate p-value
            p_value = np.mean(np.array(permutation_wcss) <= actual_wcss)
            
            self.logger.info(f"Clustering validation p-value: {p_value:.4f}")
            return p_value <= self.min_permutation_pvalue
            
        except Exception as e:
            self.logger.error(f"Error in clustering validation: {e}")
            return False
    
    def _calculate_wcss(self, features: np.ndarray, clusters: np.ndarray) -> float:
        """Calculate within-cluster sum of squares."""
        wcss = 0
        for i in range(self.n_clusters):
            cluster_points = features[clusters == i]
            if len(cluster_points) > 0:
                centroid = np.mean(cluster_points, axis=0)
                wcss += np.sum((cluster_points - centroid) ** 2)
        return wcss
    
    def _select_target_cluster(self, features: np.ndarray, clusters: np.ndarray) -> int:
        """Select cluster with RSI closest to 70 (momentum cluster)."""
        target_rsi = 70
        rsi_column = 0
        
        cluster_rsi_means = []
        for i in range(self.n_clusters):
            cluster_features = features[clusters == i]
            if len(cluster_features) > 0:
                # Convert back from standardized values
                cluster_rsi_mean = np.mean(cluster_features[:, rsi_column])
                cluster_rsi_means.append(cluster_rsi_mean)
            else:
                cluster_rsi_means.append(-999)  # Invalid cluster
        
        # Find cluster closest to target RSI
        target_cluster = np.argmin([abs(rsi - target_rsi) for rsi in cluster_rsi_means])
        
        self.logger.info(f"Selected cluster {target_cluster} with average RSI: {cluster_rsi_means[target_cluster]:.2f}")
        return target_cluster
    
    def _optimize_portfolio_weights(self, features: np.ndarray, clusters: np.ndarray, 
                                  target_cluster: int, symbols: List[str]) -> Dict[str, float]:
        """Optimize portfolio weights using mean-variance optimization."""
        # Get symbols in target cluster
        cluster_mask = clusters == target_cluster
        cluster_symbols = [symbols[i] for i in range(len(symbols)) if cluster_mask[i]]
        
        if not cluster_symbols:
            return {}
        
        # Simple equal weight with constraints (would use proper MPT in production)
        n_symbols = len(cluster_symbols)
        equal_weight = 1.0 / n_symbols
        
        # Apply constraints: min 0.5 * equal_weight, max 10%
        min_weight = max(0.005, 0.5 * equal_weight)  # At least 0.5%
        max_weight = min(0.10, equal_weight * 2)  # At most 10%
        
        weights = {}
        total_weight = 0
        
        for symbol in cluster_symbols:
            weight = max(min_weight, min(max_weight, equal_weight))
            weights[symbol] = weight
            total_weight += weight
        
        # Normalize to sum to 1.0
        if total_weight > 0:
            for symbol in weights:
                weights[symbol] /= total_weight
        
        self.logger.info(f"Optimized weights for {len(weights)} symbols in target cluster")
        return weights
    
    def _generate_rebalancing_signals(self, weights: Dict[str, float], 
                                    price_data: Dict) -> List[SignalData]:
        """Generate rebalancing signals based on optimized weights."""
        signals = []
        
        for symbol, weight in weights.items():
            if symbol in price_data and price_data[symbol].bars:
                current_price = price_data[symbol].bars[-1].close
                
                signal = SignalData(
                    symbol=symbol,
                    signal_type=SignalType.ENTRY_LONG,
                    price=current_price,
                    timestamp=datetime.now(),
                    confidence=0.8,
                    metadata={
                        "strategy": "cluster_momentum",
                        "target_weight": weight,
                        "cluster_based": True,
                        "rebalance_signal": True,
                        "holding_period": "1-4_weeks"
                    }
                )
                signals.append(signal)
        
        return signals