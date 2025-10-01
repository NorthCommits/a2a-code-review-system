"""
A2A Transport Layer

This module implements the HTTPS transport layer for A2A protocol
communication between agents.
"""

import ssl
import asyncio
from typing import Dict, Any, Optional
import httpx
from .message_schema import A2AMessage, TaskResponse
from utils.logger import get_logger

logger = get_logger(__name__)


class TransportError(Exception):
    """Custom exception for transport layer errors"""
    pass


class A2ATransport:
    """
    HTTPS transport layer for A2A protocol communication
    
    Handles secure communication between agents with proper
    error handling and retry logic.
    """
    
    def __init__(
        self, 
        timeout: int = 30, 
        max_retries: int = 3,
        retry_delay: float = 1.0,
        verify_ssl: bool = True
    ):
        """
        Initialize A2A transport layer
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.verify_ssl = verify_ssl
        
        # Configure SSL context
        self.ssl_context = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create HTTP client with custom configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            verify=self.ssl_context if verify_ssl else False,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            )
        )
    
    async def send_message(
        self, 
        endpoint: str, 
        message: A2AMessage,
        headers: Optional[Dict[str, str]] = None
    ) -> TaskResponse:
        """
        Send A2A message to endpoint
        
        Args:
            endpoint: Target endpoint URL
            message: A2A message to send
            headers: Optional additional headers
            
        Returns:
            Response from the endpoint
        """
        if headers is None:
            headers = {}
        
        headers.update({
            "Content-Type": "application/json",
            "User-Agent": "A2A-Protocol-Client/1.0",
            "Accept": "application/json"
        })
        
        message_data = message.dict()
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Sending message to {endpoint} (attempt {attempt + 1})")
                
                response = await self.client.post(
                    endpoint,
                    json=message_data,
                    headers=headers
                )
                
                # Check for HTTP errors
                if response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"HTTP error: {error_msg}")
                    
                    if response.status_code >= 500 and attempt < self.max_retries:
                        # Retry on server errors
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise TransportError(error_msg)
                
                # Parse response
                response_data = response.json()
                return TaskResponse(**response_data)
                
            except httpx.TimeoutException:
                logger.warning(f"Timeout sending message to {endpoint} (attempt {attempt + 1})")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    raise TransportError("Request timeout after all retries")
                    
            except httpx.ConnectError as e:
                logger.warning(f"Connection error to {endpoint}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    raise TransportError(f"Connection failed: {e}")
                    
            except httpx.RequestError as e:
                logger.error(f"Request error to {endpoint}: {e}")
                raise TransportError(f"Request failed: {e}")
                
            except Exception as e:
                logger.error(f"Unexpected error sending message to {endpoint}: {e}")
                raise TransportError(f"Unexpected error: {e}")
        
        raise TransportError("Max retries exceeded")
    
    async def send_notification(
        self, 
        endpoint: str, 
        notification_data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send notification to endpoint (fire and forget)
        
        Args:
            endpoint: Target endpoint URL
            notification_data: Notification data
            headers: Optional additional headers
            
        Returns:
            True if notification was sent successfully
        """
        if headers is None:
            headers = {}
        
        headers.update({
            "Content-Type": "application/json",
            "User-Agent": "A2A-Protocol-Client/1.0"
        })
        
        try:
            logger.debug(f"Sending notification to {endpoint}")
            
            response = await self.client.post(
                endpoint,
                json=notification_data,
                headers=headers
            )
            
            # For notifications, we don't care about the response content
            # Just check if it was sent successfully
            return response.status_code < 400
            
        except Exception as e:
            logger.error(f"Error sending notification to {endpoint}: {e}")
            return False
    
    async def health_check(self, endpoint: str) -> bool:
        """
        Perform health check on endpoint
        
        Args:
            endpoint: Endpoint to check
            
        Returns:
            True if endpoint is healthy
        """
        health_endpoint = f"{endpoint.rstrip('/')}/health"
        
        try:
            response = await self.client.get(health_endpoint, timeout=5.0)
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Health check failed for {endpoint}: {e}")
            return False
    
    async def batch_send(
        self, 
        requests: list[tuple[str, A2AMessage]],
        max_concurrent: int = 10
    ) -> list[TaskResponse]:
        """
        Send multiple messages concurrently
        
        Args:
            requests: List of (endpoint, message) tuples
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of responses
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def send_with_semaphore(endpoint: str, message: A2AMessage) -> TaskResponse:
            async with semaphore:
                return await self.send_message(endpoint, message)
        
        tasks = [
            send_with_semaphore(endpoint, message) 
            for endpoint, message in requests
        ]
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Separate successful responses from exceptions
            results = []
            for response in responses:
                if isinstance(response, Exception):
                    logger.error(f"Batch send error: {response}")
                    # Create error response
                    error_response = TaskResponse(
                        id=None,
                        error={
                            "code": -1,
                            "message": str(response)
                        }
                    )
                    results.append(error_response)
                else:
                    results.append(response)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch send failed: {e}")
            raise TransportError(f"Batch send failed: {e}")
    
    async def close(self):
        """Close transport layer and cleanup resources"""
        await self.client.aclose()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get transport layer statistics"""
        return {
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "verify_ssl": self.verify_ssl,
            "active_connections": len(self.client._pool._pool) if hasattr(self.client, '_pool') else 0
        }
