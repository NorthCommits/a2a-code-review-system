"""
Result Aggregator

This module implements result aggregation logic for the coordinator agent.
Combines and synthesizes results from multiple remote agents.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
from a2a_protocol.message_schema import AnalysisResult, TaskStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class ResultAggregator:
    """
    Aggregates and synthesizes analysis results from multiple agents
    
    Combines results from different specialized agents into a
    comprehensive analysis report.
    """
    
    def __init__(self):
        """Initialize result aggregator"""
        self.logger = get_logger(__name__)
        
        # Aggregation strategies
        self.aggregation_strategies = {
            "observations": "merge_and_deduplicate",
            "errors": "merge_and_prioritize",
            "suggestions": "merge_and_rank",
            "corrected_code": "apply_sequential_fixes"
        }
        
        self.logger.info("Initialized Result Aggregator")
    
    def aggregate_results(self, results: Dict[str, AnalysisResult]) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents
        
        Args:
            results: Dictionary mapping agent IDs to analysis results
            
        Returns:
            Aggregated analysis result
        """
        try:
            if not results:
                return self._create_empty_result()
            
            self.logger.info(f"Aggregating results from {len(results)} agents")
            
            # Extract all observations, errors, and suggestions
            all_observations = []
            all_errors = []
            all_suggestions = []
            agent_metadata = {}
            
            for agent_id, result in results.items():
                if result and result.status == TaskStatus.COMPLETED:
                    all_observations.extend(result.observations)
                    all_errors.extend(result.errors)
                    all_suggestions.extend(result.suggestions)
                    agent_metadata[agent_id] = result.metadata
            
            # Apply aggregation strategies
            aggregated_observations = self._aggregate_observations(all_observations)
            aggregated_errors = self._aggregate_errors(all_errors)
            aggregated_suggestions = self._aggregate_suggestions(all_suggestions)
            
            # Generate corrected code
            corrected_code = self._generate_corrected_code(results)
            
            # Calculate summary statistics
            summary = self._calculate_summary_stats(
                aggregated_observations,
                aggregated_errors,
                aggregated_suggestions
            )
            
            # Create final aggregated result
            aggregated_result = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_agents": len(results),
                "successful_agents": len([r for r in results.values() if r and r.status == TaskStatus.COMPLETED]),
                "observations": aggregated_observations,
                "errors": aggregated_errors,
                "suggestions": aggregated_suggestions,
                "corrected_code": corrected_code,
                "summary": summary,
                "agent_metadata": agent_metadata
            }
            
            self.logger.info("Successfully aggregated analysis results")
            return aggregated_result
            
        except Exception as e:
            self.logger.error(f"Error aggregating results: {e}")
            return self._create_error_result(str(e))
    
    def _aggregate_observations(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregate and deduplicate observations
        
        Args:
            observations: List of observations from all agents
            
        Returns:
            Aggregated observations
        """
        try:
            # Group observations by type and location
            observation_groups = defaultdict(list)
            
            for obs in observations:
                key = f"{obs.get('type', 'unknown')}_{obs.get('line_number', 'unknown')}"
                observation_groups[key].append(obs)
            
            # Merge similar observations
            aggregated = []
            for group_observations in observation_groups.values():
                if len(group_observations) == 1:
                    aggregated.append(group_observations[0])
                else:
                    # Merge multiple observations of the same type/location
                    merged = self._merge_similar_observations(group_observations)
                    aggregated.append(merged)
            
            # Sort by severity and line number
            aggregated.sort(key=lambda x: (
                self._get_severity_priority(x.get('severity', 'info')),
                x.get('line_number', 0)
            ))
            
            return aggregated
            
        except Exception as e:
            self.logger.error(f"Error aggregating observations: {e}")
            return observations
    
    def _aggregate_errors(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregate and prioritize errors
        
        Args:
            errors: List of errors from all agents
            
        Returns:
            Aggregated errors
        """
        try:
            # Remove duplicates and prioritize by severity
            unique_errors = []
            seen_errors = set()
            
            for error in errors:
                # Create a key for deduplication
                error_key = (
                    error.get('type', ''),
                    error.get('line_number', 0),
                    error.get('message', '')[:100]  # First 100 chars for comparison
                )
                
                if error_key not in seen_errors:
                    seen_errors.add(error_key)
                    unique_errors.append(error)
            
            # Sort by severity and line number
            unique_errors.sort(key=lambda x: (
                self._get_severity_priority(x.get('severity', 'error')),
                x.get('line_number', 0)
            ))
            
            return unique_errors
            
        except Exception as e:
            self.logger.error(f"Error aggregating errors: {e}")
            return errors
    
    def _aggregate_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregate and rank suggestions
        
        Args:
            suggestions: List of suggestions from all agents
            
        Returns:
            Aggregated suggestions
        """
        try:
            # Group suggestions by type
            suggestion_groups = defaultdict(list)
            
            for suggestion in suggestions:
                suggestion_type = suggestion.get('type', 'general')
                suggestion_groups[suggestion_type].append(suggestion)
            
            # Rank suggestions within each group
            ranked_suggestions = []
            for suggestion_type, group_suggestions in suggestion_groups.items():
                # Sort by priority/impact
                group_suggestions.sort(key=lambda x: x.get('priority', 5), reverse=True)
                
                # Take top suggestions from each group
                top_suggestions = group_suggestions[:3]  # Top 3 per type
                ranked_suggestions.extend(top_suggestions)
            
            # Sort overall by priority
            ranked_suggestions.sort(key=lambda x: x.get('priority', 5), reverse=True)
            
            return ranked_suggestions
            
        except Exception as e:
            self.logger.error(f"Error aggregating suggestions: {e}")
            return suggestions
    
    def _generate_corrected_code(self, results: Dict[str, AnalysisResult]) -> Optional[str]:
        """
        Generate corrected code by applying fixes from agents
        
        Args:
            results: Analysis results from all agents
            
        Returns:
            Corrected code or None
        """
        try:
            # Find the first agent that provided corrected code
            for result in results.values():
                if result and result.corrected_code:
                    return result.corrected_code
            
            # If no agent provided corrected code, return None
            # In a real implementation, you might apply fixes sequentially
            return None
            
        except Exception as e:
            self.logger.error(f"Error generating corrected code: {e}")
            return None
    
    def _merge_similar_observations(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge similar observations into a single observation
        
        Args:
            observations: List of similar observations
            
        Returns:
            Merged observation
        """
        if not observations:
            return {}
        
        if len(observations) == 1:
            return observations[0]
        
        # Use the first observation as base
        merged = observations[0].copy()
        
        # Combine messages from all observations
        messages = [obs.get('message', '') for obs in observations if obs.get('message')]
        if messages:
            merged['message'] = ' | '.join(set(messages))  # Remove duplicates
        
        # Update severity to highest level
        severities = [obs.get('severity', 'info') for obs in observations]
        merged['severity'] = self._get_highest_severity(severities)
        
        # Add count of similar observations
        merged['count'] = len(observations)
        merged['sources'] = [obs.get('agent_id', 'unknown') for obs in observations]
        
        return merged
    
    def _calculate_summary_stats(
        self, 
        observations: List[Dict[str, Any]], 
        errors: List[Dict[str, Any]], 
        suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate summary statistics
        
        Args:
            observations: Aggregated observations
            errors: Aggregated errors
            suggestions: Aggregated suggestions
            
        Returns:
            Summary statistics
        """
        try:
            # Count by severity
            error_counts = defaultdict(int)
            for error in errors:
                severity = error.get('severity', 'error')
                error_counts[severity] += 1
            
            observation_counts = defaultdict(int)
            for obs in observations:
                severity = obs.get('severity', 'info')
                observation_counts[severity] += 1
            
            # Calculate overall scores
            total_issues = len(errors) + len(observations)
            critical_issues = error_counts.get('critical', 0) + observation_counts.get('critical', 0)
            
            # Calculate quality score (0-100)
            quality_score = max(0, 100 - (total_issues * 2) - (critical_issues * 10))
            
            return {
                "total_observations": len(observations),
                "total_errors": len(errors),
                "total_suggestions": len(suggestions),
                "error_counts": dict(error_counts),
                "observation_counts": dict(observation_counts),
                "critical_issues": critical_issues,
                "quality_score": min(100, max(0, quality_score))
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating summary stats: {e}")
            return {
                "total_observations": 0,
                "total_errors": 0,
                "total_suggestions": 0,
                "error_counts": {},
                "observation_counts": {},
                "critical_issues": 0,
                "quality_score": 0
            }
    
    def _get_severity_priority(self, severity: str) -> int:
        """Get numeric priority for severity level"""
        severity_map = {
            "critical": 1,
            "error": 2,
            "warning": 3,
            "info": 4,
            "debug": 5
        }
        return severity_map.get(severity.lower(), 4)
    
    def _get_highest_severity(self, severities: List[str]) -> str:
        """Get the highest severity level from a list"""
        if not severities:
            return "info"
        
        priority_map = {v: k for k, v in {
            "critical": 1,
            "error": 2,
            "warning": 3,
            "info": 4,
            "debug": 5
        }.items()}
        
        min_priority = min(self._get_severity_priority(s) for s in severities)
        return priority_map.get(min_priority, "info")
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result when no agents responded"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_agents": 0,
            "successful_agents": 0,
            "observations": [],
            "errors": [],
            "suggestions": [],
            "corrected_code": None,
            "summary": {
                "total_observations": 0,
                "total_errors": 0,
                "total_suggestions": 0,
                "error_counts": {},
                "observation_counts": {},
                "critical_issues": 0,
                "quality_score": 0
            },
            "agent_metadata": {}
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result when aggregation fails"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_agents": 0,
            "successful_agents": 0,
            "observations": [],
            "errors": [{
                "type": "aggregation_error",
                "severity": "critical",
                "message": f"Failed to aggregate results: {error_message}",
                "line_number": 0
            }],
            "suggestions": [],
            "corrected_code": None,
            "summary": {
                "total_observations": 0,
                "total_errors": 1,
                "total_suggestions": 0,
                "error_counts": {"critical": 1},
                "observation_counts": {},
                "critical_issues": 1,
                "quality_score": 0
            },
            "agent_metadata": {}
        }
