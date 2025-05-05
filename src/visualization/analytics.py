"""
Analytics module for the Temporal-Spatial Memory System.

This module provides tools for analyzing clustering patterns, entity relationships,
and information distribution in the 4D coordinate space.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from scipy.spatial import distance
from scipy.stats import entropy

from src.data_models import PolarTemporalCoordinate
from src.models.narrative_atlas import Node, NarrativeAtlas

# Configure logging
logger = logging.getLogger("Analytics")


class ClusterAnalyzer:
    """
    Analyzes clustering patterns in the 4D polar-temporal coordinate space.
    
    Features:
    - Automatic cluster detection using various algorithms
    - Entity relationship analysis
    - Information density and distribution metrics
    - Temporal pattern analysis
    """
    
    def __init__(self, 
                 output_dir: str = "output/analytics",
                 random_state: int = 42):
        """
        Initialize the cluster analyzer.
        
        Args:
            output_dir: Directory to save analysis outputs
            random_state: Random seed for reproducibility
        """
        self.output_dir = output_dir
        self.random_state = random_state
        
    def prepare_data(self, nodes: List[Node]) -> pd.DataFrame:
        """
        Extract node coordinates and convert to a format suitable for analysis.
        
        Args:
            nodes: List of nodes to analyze
            
        Returns:
            DataFrame with coordinate vectors and metadata
        """
        data = []
        
        for node in nodes:
            if node.coordinates:
                # Extract 4D coordinates
                r = node.coordinates.r
                theta = node.coordinates.theta
                t = node.coordinates.t
                z = node.coordinates.z
                
                # Convert polar to cartesian for some analyses
                x = r * np.cos(theta)
                y = r * np.sin(theta)
                
                # Create entry
                entry = {
                    'id': node.id,
                    'type': node.type,
                    'r': r,
                    'theta': theta,
                    't': t,
                    'z': z,
                    'x': x, 
                    'y': y,
                    'z_type': node.coordinates.z_type if hasattr(node.coordinates, 'z_type') else "",
                    # Create feature vector (used for clustering)
                    'feature_vector': np.array([x, y, t, z])
                }
                data.append(entry)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        logger.info(f"Prepared data for {len(df)} nodes.")
        return df
    
    def detect_clusters(self, 
                      df: pd.DataFrame, 
                      n_clusters: Optional[int] = None,
                      distance_threshold: float = 0.5,
                      algorithm: str = "kmeans") -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Detect clusters in the 4D coordinate space.
        
        Args:
            df: DataFrame with feature vectors
            n_clusters: Number of clusters (auto-detected if None)
            distance_threshold: Distance threshold for hierarchical clustering
            algorithm: Clustering algorithm ('kmeans', 'dbscan', 'hierarchical')
            
        Returns:
            Tuple of (DataFrame with cluster labels, clustering metrics)
        """
        if df.empty:
            logger.warning("No data provided for cluster detection.")
            return df, {}
        
        # Extract feature vectors
        feature_matrix = np.vstack(df['feature_vector'].values)
        
        # Normalize features for better clustering
        feature_mean = np.mean(feature_matrix, axis=0)
        feature_std = np.std(feature_matrix, axis=0)
        normalized_features = (feature_matrix - feature_mean) / feature_std
        
        # Auto-detect number of clusters if not specified
        if n_clusters is None and algorithm == "kmeans":
            # Use silhouette score to determine optimal number of clusters
            silhouette_scores = []
            k_range = range(2, min(20, len(df) // 5 + 1))  # Cap at 20 clusters or 1/5 of data points
            
            for k in k_range:
                km = KMeans(n_clusters=k, random_state=self.random_state)
                km.fit(normalized_features)
                score = silhouette_score(normalized_features, km.labels_)
                silhouette_scores.append(score)
            
            # Find the k with the best score
            n_clusters = k_range[np.argmax(silhouette_scores)]
            logger.info(f"Auto-detected {n_clusters} clusters using silhouette analysis.")
        
        # Apply the chosen clustering algorithm
        cluster_labels = None
        metrics = {}
        
        if algorithm == "kmeans":
            # Use KMeans clustering
            n_clusters = n_clusters or 5  # Default to 5 clusters if not specified
            km = KMeans(n_clusters=n_clusters, random_state=self.random_state)
            cluster_labels = km.fit_predict(normalized_features)
            
            # Calculate metrics
            metrics['inertia'] = km.inertia_
            metrics['silhouette_score'] = silhouette_score(normalized_features, cluster_labels)
            metrics['cluster_centers'] = km.cluster_centers_
            metrics['algorithm'] = 'kmeans'
            metrics['n_clusters'] = n_clusters
            
        elif algorithm == "dbscan":
            # Use DBSCAN for density-based clustering
            eps = distance_threshold or 0.5  # Default epsilon
            min_samples = 3  # Minimum points to form a dense region
            
            dbscan = DBSCAN(eps=eps, min_samples=min_samples)
            cluster_labels = dbscan.fit_predict(normalized_features)
            
            # Calculate metrics
            n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
            metrics['n_clusters'] = n_clusters
            metrics['n_noise'] = list(cluster_labels).count(-1)
            if n_clusters > 1:  # Silhouette score needs at least 2 clusters
                metrics['silhouette_score'] = silhouette_score(
                    normalized_features, 
                    cluster_labels,
                    sample_size=min(1000, len(normalized_features))
                )
            metrics['algorithm'] = 'dbscan'
            metrics['eps'] = eps
            
        elif algorithm == "hierarchical":
            # Use hierarchical/agglomerative clustering
            n_clusters = n_clusters or 5  # Default to 5 clusters if not specified
            
            agglo = AgglomerativeClustering(
                n_clusters=n_clusters,
                distance_threshold=distance_threshold if n_clusters is None else None,
                compute_full_tree=True
            )
            cluster_labels = agglo.fit_predict(normalized_features)
            
            # Calculate metrics
            metrics['n_clusters'] = len(set(cluster_labels))
            metrics['silhouette_score'] = silhouette_score(normalized_features, cluster_labels)
            metrics['algorithm'] = 'hierarchical'
            metrics['distance_threshold'] = distance_threshold
            
        else:
            logger.error(f"Unknown clustering algorithm: {algorithm}")
            return df, {}
        
        # Add cluster labels to the dataframe
        df['cluster'] = cluster_labels
        
        # Calculate additional cluster statistics
        cluster_stats = df.groupby('cluster').agg({
            'id': 'count',  # Count of nodes in each cluster
            'r': ['mean', 'std'],
            'theta': ['mean', 'std'],
            't': ['mean', 'std'],
            'z': ['mean', 'std']
        })
        
        metrics['cluster_stats'] = cluster_stats
        
        logger.info(f"Detected {metrics['n_clusters']} clusters using {algorithm}.")
        return df, metrics
    
    def analyze_information_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze how information is distributed in the coordinate space.
        
        Args:
            df: DataFrame with node coordinates
            
        Returns:
            Dictionary of distribution metrics
        """
        if df.empty:
            return {}
        
        # Calculate basic distribution statistics
        metrics = {
            'r_stats': {
                'mean': df['r'].mean(),
                'median': df['r'].median(),
                'std': df['r'].std(),
                'min': df['r'].min(),
                'max': df['r'].max()
            },
            'theta_stats': {
                'mean': df['theta'].mean(),
                'median': df['theta'].median(),
                'std': df['theta'].std(),
                'min': df['theta'].min(),
                'max': df['theta'].max(),
                'circular_mean': np.angle(np.mean(np.exp(1j * df['theta'])))
            },
            't_stats': {
                'mean': df['t'].mean(),
                'median': df['t'].median(),
                'std': df['t'].std(),
                'min': df['t'].min(),
                'max': df['t'].max()
            },
            'z_stats': {
                'mean': df['z'].mean(),
                'median': df['z'].median(),
                'std': df['z'].std(),
                'min': df['z'].min(),
                'max': df['z'].max()
            }
        }
        
        # Calculate information density across different dimensions
        
        # r (radius) density - divide r into 10 bins and count nodes
        r_bins = np.linspace(df['r'].min(), df['r'].max(), 11)
        r_counts, _ = np.histogram(df['r'], bins=r_bins)
        metrics['r_density'] = {
            'bins': r_bins[:-1],
            'counts': r_counts,
            'entropy': entropy(r_counts + 1)  # Add 1 to avoid log(0)
        }
        
        # theta (angular) density - divide theta into 12 bins (30 degrees each)
        theta_bins = np.linspace(0, 2*np.pi, 13)
        theta_counts, _ = np.histogram(df['theta'], bins=theta_bins)
        metrics['theta_density'] = {
            'bins': theta_bins[:-1],
            'counts': theta_counts,
            'entropy': entropy(theta_counts + 1)
        }
        
        # t (temporal) density - divide t into 10 bins
        t_bins = np.linspace(df['t'].min(), df['t'].max(), 11)
        t_counts, _ = np.histogram(df['t'], bins=t_bins)
        metrics['t_density'] = {
            'bins': t_bins[:-1],
            'counts': t_counts,
            'entropy': entropy(t_counts + 1)
        }
        
        # Calculate overall information entropy
        metrics['overall_entropy'] = {
            'r': metrics['r_density']['entropy'],
            'theta': metrics['theta_density']['entropy'],
            't': metrics['t_density']['entropy'],
            'total': (metrics['r_density']['entropy'] + 
                     metrics['theta_density']['entropy'] + 
                     metrics['t_density']['entropy']) / 3
        }
        
        # Calculate node type distribution
        type_counts = df['type'].value_counts()
        metrics['type_distribution'] = {
            'counts': type_counts.to_dict(),
            'entropy': entropy(type_counts.values + 1)
        }
        
        logger.info(f"Analyzed information distribution for {len(df)} nodes.")
        return metrics
    
    def analyze_temporal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze patterns and trends along the temporal dimension.
        
        Args:
            df: DataFrame with node coordinates
            
        Returns:
            Dictionary of temporal pattern metrics
        """
        if df.empty:
            return {}
        
        # Sort by temporal coordinate
        sorted_df = df.sort_values('t')
        
        # Calculate temporal distance between adjacent nodes
        t_diffs = np.diff(sorted_df['t'].values)
        
        # Calculate basic temporal metrics
        metrics = {
            'temporal_span': df['t'].max() - df['t'].min(),
            'temporal_density': len(df) / (df['t'].max() - df['t'].min() + 1e-10),
            'temporal_gaps': {
                'mean': np.mean(t_diffs),
                'median': np.median(t_diffs),
                'std': np.std(t_diffs),
                'max': np.max(t_diffs)
            }
        }
        
        # Identify temporal clusters (periods of high activity)
        from scipy.signal import find_peaks
        
        # Create a histogram of temporal distribution
        t_bins = np.linspace(df['t'].min(), df['t'].max(), 50)
        t_hist, _ = np.histogram(df['t'], bins=t_bins)
        
        # Find peaks in the histogram
        peaks, properties = find_peaks(t_hist, height=np.mean(t_hist), distance=3)
        
        # Extract information about temporal clusters
        temporal_clusters = []
        for i, peak_idx in enumerate(peaks):
            temporal_clusters.append({
                'center': t_bins[peak_idx],
                'height': properties['peak_heights'][i],
                'start': t_bins[max(0, peak_idx-2)],
                'end': t_bins[min(len(t_bins)-1, peak_idx+2)]
            })
        
        metrics['temporal_clusters'] = temporal_clusters
        metrics['n_temporal_clusters'] = len(temporal_clusters)
        
        # Calculate trend of r over time
        from scipy import stats
        
        # Calculate correlation between t and r
        t_r_corr, p_value = stats.pearsonr(df['t'], df['r'])
        
        # Perform linear regression of r over t
        slope, intercept, r_value, p_value, std_err = stats.linregress(df['t'], df['r'])
        
        metrics['r_over_time'] = {
            'correlation': t_r_corr,
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value**2,
            'p_value': p_value
        }
        
        # Calculate trend of theta over time (circular correlation)
        theta_cos = np.cos(df['theta'])
        theta_sin = np.sin(df['theta'])
        
        t_theta_cos_corr, _ = stats.pearsonr(df['t'], theta_cos)
        t_theta_sin_corr, _ = stats.pearsonr(df['t'], theta_sin)
        
        metrics['theta_over_time'] = {
            'correlation_cos': t_theta_cos_corr,
            'correlation_sin': t_theta_sin_corr,
            'circular_trend': np.sqrt(t_theta_cos_corr**2 + t_theta_sin_corr**2)
        }
        
        logger.info(f"Analyzed temporal patterns for {len(df)} nodes.")
        return metrics
    
    def analyze_atlas(self, atlas: NarrativeAtlas) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a NarrativeAtlas.
        
        Args:
            atlas: NarrativeAtlas instance to analyze
            
        Returns:
            Dictionary of analysis results
        """
        # Extract nodes from atlas
        nodes = list(atlas.db.nodes.values())
        
        if not nodes:
            logger.warning("No nodes found in the atlas for analysis.")
            return {}
        
        logger.info(f"Analyzing atlas with {len(nodes)} nodes.")
        
        # Prepare data
        df = self.prepare_data(nodes)
        
        # Detect clusters
        clustered_df, cluster_metrics = self.detect_clusters(df)
        
        # Analyze information distribution
        distribution_metrics = self.analyze_information_distribution(df)
        
        # Analyze temporal patterns
        temporal_metrics = self.analyze_temporal_patterns(df)
        
        # Combine all metrics
        analysis_results = {
            'node_count': len(nodes),
            'node_types': df['type'].value_counts().to_dict(),
            'clustering': cluster_metrics,
            'distribution': distribution_metrics,
            'temporal': temporal_metrics
        }
        
        # Add node similarity network analysis
        similarity_metrics = self.calculate_node_similarity_network(df)
        analysis_results['similarity_network'] = similarity_metrics
        
        logger.info(f"Completed comprehensive analysis of atlas with {len(nodes)} nodes.")
        return analysis_results
    
    def calculate_node_similarity_network(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate node similarity network metrics.
        
        Args:
            df: DataFrame with node coordinates
            
        Returns:
            Dictionary of network metrics
        """
        if df.empty or len(df) < 2:
            return {}
        
        # Extract feature vectors
        feature_matrix = np.vstack(df['feature_vector'].values)
        
        # Calculate pairwise distances
        distances = distance.pdist(feature_matrix)
        distance_matrix = distance.squareform(distances)
        
        # Calculate similarity matrix (inverse of distance)
        similarity_matrix = 1 / (1 + distance_matrix)
        
        # Basic network metrics
        metrics = {
            'avg_similarity': np.mean(similarity_matrix),
            'min_similarity': np.min(similarity_matrix),
            'max_similarity': np.max(similarity_matrix[~np.eye(len(df), dtype=bool)])  # Exclude diagonal
        }
        
        # Calculate network density (proportion of strong connections)
        strong_threshold = np.percentile(similarity_matrix.flatten(), 80)  # Top 20% are "strong"
        strong_connections = (similarity_matrix >= strong_threshold).sum() - len(df)  # Exclude self-connections
        max_possible_connections = len(df) * (len(df) - 1)
        
        metrics['network_density'] = strong_connections / max_possible_connections
        
        # Calculate node centrality (average similarity to all other nodes)
        centrality = np.mean(similarity_matrix, axis=1)
        
        metrics['centrality'] = {
            'mean': np.mean(centrality),
            'std': np.std(centrality),
            'max': np.max(centrality),
            'min': np.min(centrality)
        }
        
        # Find most central and most isolated nodes
        most_central_idx = np.argmax(centrality)
        most_isolated_idx = np.argmin(centrality)
        
        metrics['most_central_node'] = {
            'id': df.iloc[most_central_idx]['id'],
            'centrality': centrality[most_central_idx]
        }
        
        metrics['most_isolated_node'] = {
            'id': df.iloc[most_isolated_idx]['id'],
            'centrality': centrality[most_isolated_idx]
        }
        
        logger.info(f"Calculated similarity network metrics for {len(df)} nodes.")
        return metrics 