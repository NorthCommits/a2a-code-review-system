"""
Session Manager

This module implements session state management for the A2A Code Review System.
Manages Streamlit session state and temporary data storage.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manages session state for the A2A Code Review System
    
    Handles storage and retrieval of session data, analysis results,
    and user preferences in Streamlit session state.
    """
    
    def __init__(self):
        """Initialize session manager"""
        self.logger = get_logger(__name__)
        self._initialize_default_state()
        self.logger.info("Session manager initialized")
    
    def _initialize_default_state(self):
        """Initialize default session state values"""
        default_values = {
            'analysis_results': None,
            'analysis_history': [],
            'system_status': 'initializing',
            'current_analysis_id': None,
            'user_preferences': {
                'language': 'python',
                'include_security': True,
                'include_performance': True,
                'include_documentation': True,
                'include_test_coverage': False
            },
            'session_start_time': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'analysis_options': {},
            'uploaded_files': [],
            'system_settings': {
                'auto_save': True,
                'show_advanced_options': False,
                'theme': 'light'
            }
        }
        
        # Initialize session state with default values
        for key, value in default_values.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def set_analysis_results(self, results: Dict[str, Any]) -> bool:
        """
        Store analysis results in session state
        
        Args:
            results: Analysis results dictionary
            
        Returns:
            True if successful
        """
        try:
            st.session_state.analysis_results = results
            
            # Add to history if not already present
            analysis_id = results.get('analysis_id')
            if analysis_id and not self._is_analysis_in_history(analysis_id):
                st.session_state.analysis_history.append(results)
                
                # Limit history size
                max_history = 10
                if len(st.session_state.analysis_history) > max_history:
                    st.session_state.analysis_history = st.session_state.analysis_history[-max_history:]
            
            self._update_last_activity()
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing analysis results: {e}")
            return False
    
    def get_analysis_results(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve current analysis results
        
        Returns:
            Current analysis results or None
        """
        return st.session_state.get('analysis_results')
    
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """
        Retrieve analysis history
        
        Returns:
            List of historical analysis results
        """
        return st.session_state.get('analysis_history', [])
    
    def clear_analysis_results(self):
        """Clear current analysis results"""
        st.session_state.analysis_results = None
        self._update_last_activity()
    
    def clear_analysis_history(self):
        """Clear analysis history"""
        st.session_state.analysis_history = []
        self._update_last_activity()
    
    def set_system_status(self, status: str) -> bool:
        """
        Set system status
        
        Args:
            status: System status string
            
        Returns:
            True if successful
        """
        try:
            valid_statuses = ['initializing', 'ready', 'analyzing', 'completed', 'error']
            if status in valid_statuses:
                st.session_state.system_status = status
                self._update_last_activity()
                return True
            else:
                self.logger.warning(f"Invalid system status: {status}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting system status: {e}")
            return False
    
    def get_system_status(self) -> str:
        """
        Get current system status
        
        Returns:
            Current system status
        """
        return st.session_state.get('system_status', 'unknown')
    
    def set_current_analysis_id(self, analysis_id: str) -> bool:
        """
        Set current analysis ID
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            True if successful
        """
        try:
            st.session_state.current_analysis_id = analysis_id
            self._update_last_activity()
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting analysis ID: {e}")
            return False
    
    def get_current_analysis_id(self) -> Optional[str]:
        """
        Get current analysis ID
        
        Returns:
            Current analysis ID or None
        """
        return st.session_state.get('current_analysis_id')
    
    def set_user_preference(self, key: str, value: Any) -> bool:
        """
        Set user preference
        
        Args:
            key: Preference key
            value: Preference value
            
        Returns:
            True if successful
        """
        try:
            if 'user_preferences' not in st.session_state:
                st.session_state.user_preferences = {}
            
            st.session_state.user_preferences[key] = value
            self._update_last_activity()
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting user preference: {e}")
            return False
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """
        Get user preference
        
        Args:
            key: Preference key
            default: Default value if preference not found
            
        Returns:
            Preference value or default
        """
        preferences = st.session_state.get('user_preferences', {})
        return preferences.get(key, default)
    
    def set_analysis_options(self, options: Dict[str, Any]) -> bool:
        """
        Set analysis options
        
        Args:
            options: Analysis options dictionary
            
        Returns:
            True if successful
        """
        try:
            st.session_state.analysis_options = options
            self._update_last_activity()
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting analysis options: {e}")
            return False
    
    def get_analysis_options(self) -> Dict[str, Any]:
        """
        Get analysis options
        
        Returns:
            Analysis options dictionary
        """
        return st.session_state.get('analysis_options', {})
    
    def add_uploaded_file(self, file_info: Dict[str, Any]) -> bool:
        """
        Add uploaded file to session
        
        Args:
            file_info: File information dictionary
            
        Returns:
            True if successful
        """
        try:
            if 'uploaded_files' not in st.session_state:
                st.session_state.uploaded_files = []
            
            st.session_state.uploaded_files.append(file_info)
            self._update_last_activity()
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding uploaded file: {e}")
            return False
    
    def get_uploaded_files(self) -> List[Dict[str, Any]]:
        """
        Get list of uploaded files
        
        Returns:
            List of uploaded file information
        """
        return st.session_state.get('uploaded_files', [])
    
    def clear_uploaded_files(self):
        """Clear uploaded files list"""
        st.session_state.uploaded_files = []
        self._update_last_activity()
    
    def set_system_setting(self, key: str, value: Any) -> bool:
        """
        Set system setting
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            True if successful
        """
        try:
            if 'system_settings' not in st.session_state:
                st.session_state.system_settings = {}
            
            st.session_state.system_settings[key] = value
            self._update_last_activity()
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting system setting: {e}")
            return False
    
    def get_system_setting(self, key: str, default: Any = None) -> Any:
        """
        Get system setting
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        settings = st.session_state.get('system_settings', {})
        return settings.get(key, default)
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get session information
        
        Returns:
            Session information dictionary
        """
        try:
            session_start = st.session_state.get('session_start_time', datetime.utcnow())
            last_activity = st.session_state.get('last_activity', datetime.utcnow())
            
            return {
                'session_id': id(st.session_state),  # Use object ID as session ID
                'session_start_time': session_start.isoformat(),
                'last_activity_time': last_activity.isoformat(),
                'session_duration': (datetime.utcnow() - session_start).total_seconds(),
                'analysis_count': len(st.session_state.get('analysis_history', [])),
                'system_status': self.get_system_status(),
                'current_analysis_id': self.get_current_analysis_id(),
                'user_preferences': st.session_state.get('user_preferences', {}),
                'system_settings': st.session_state.get('system_settings', {})
            }
            
        except Exception as e:
            self.logger.error(f"Error getting session info: {e}")
            return {}
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """
        Cleanup old session data
        
        Args:
            max_age_hours: Maximum age of data to keep
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            # Clean up old analysis history
            if 'analysis_history' in st.session_state:
                history = st.session_state.analysis_history
                filtered_history = []
                
                for analysis in history:
                    timestamp_str = analysis.get('timestamp', '')
                    if timestamp_str:
                        try:
                            analysis_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if analysis_time > cutoff_time:
                                filtered_history.append(analysis)
                        except:
                            # Keep analysis if timestamp parsing fails
                            filtered_history.append(analysis)
                    else:
                        # Keep analysis if no timestamp
                        filtered_history.append(analysis)
                
                st.session_state.analysis_history = filtered_history
            
            # Clean up old uploaded files
            if 'uploaded_files' in st.session_state:
                files = st.session_state.uploaded_files
                filtered_files = []
                
                for file_info in files:
                    upload_time_str = file_info.get('upload_time', '')
                    if upload_time_str:
                        try:
                            upload_time = datetime.fromisoformat(upload_time_str)
                            if upload_time > cutoff_time:
                                filtered_files.append(file_info)
                        except:
                            # Keep file if timestamp parsing fails
                            filtered_files.append(file_info)
                    else:
                        # Keep file if no timestamp
                        filtered_files.append(file_info)
                
                st.session_state.uploaded_files = filtered_files
            
            self._update_last_activity()
            self.logger.info("Cleaned up old session data")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    def reset_session(self):
        """Reset session to initial state"""
        try:
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Reinitialize default state
            self._initialize_default_state()
            
            self.logger.info("Session reset to initial state")
            
        except Exception as e:
            self.logger.error(f"Error resetting session: {e}")
    
    def _is_analysis_in_history(self, analysis_id: str) -> bool:
        """Check if analysis is already in history"""
        history = st.session_state.get('analysis_history', [])
        return any(analysis.get('analysis_id') == analysis_id for analysis in history)
    
    def _update_last_activity(self):
        """Update last activity timestamp"""
        st.session_state.last_activity = datetime.utcnow()
