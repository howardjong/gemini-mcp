from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

class LargeContextManager:
    """Manage large context windows efficiently"""
    
    def __init__(self, max_size: int = None, preferred_size: int = None):
        settings = get_settings()
        self.max_size = max_size or settings.MAX_CONTEXT_SIZE
        self.preferred_size = preferred_size or settings.PREFERRED_CONTEXT_SIZE
        self.storage = []
        self.current_size = 0
        
    def add_message(self, message):
        """Add message to context, managing size constraints"""
        # Calculate approximate token count
        msg_size = self._estimate_token_size(message)
        
        # If adding would exceed preferred size, warn
        if self.current_size + msg_size > self.preferred_size:
            logger.warning(
                f"Context size ({self.current_size + msg_size} tokens) exceeds preferred size "
                f"({self.preferred_size} tokens)"
            )
        
        # If adding would exceed max size, remove oldest messages until it fits
        while self.current_size + msg_size > self.max_size and self.storage:
            removed = self.storage.pop(0)
            removed_size = self._estimate_token_size(removed)
            self.current_size -= removed_size
            logger.info(f"Removed {removed_size} tokens from context to make room for new message")
            
        # Add new message
        self.storage.append(message)
        self.current_size += msg_size
        
    def get_context(self):
        """Get current context"""
        return self.storage
        
    def get_size(self):
        """Get current context size in tokens"""
        return self.current_size
        
    def _estimate_token_size(self, message):
        """Estimate token size of message"""
        if isinstance(message, str):
            # Approximate tokens: 1.3 tokens per word
            return int(len(message.split()) * 1.3)
        elif isinstance(message, dict):
            # For dictionaries, convert to string and use same formula
            message_str = str(message)
            return int(len(message_str.split()) * 1.3)
        return 0
        
    def clear(self):
        """Clear context"""
        self.storage = []
        self.current_size = 0
