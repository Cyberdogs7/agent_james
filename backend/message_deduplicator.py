import collections
import logging
import hashlib
import time

logger = logging.getLogger(__name__)

class MessageDeduplicator:
    def __init__(self, max_size=1000):
        self.processed_ids = collections.deque(maxlen=max_size)
        self.processed_set = set() # For O(1) lookup
        self.max_size = max_size

    def check_and_add(self, message_id):
        """
        Checks if a message ID has been processed.
        Returns True if the message is NEW (not processed).
        Returns False if the message is DUPLICATE (already processed).
        """
        if message_id in self.processed_set:
            return False

        # Add to deque and set
        if len(self.processed_ids) >= self.max_size:
            removed_id = self.processed_ids.popleft()
            if removed_id in self.processed_set:
                self.processed_set.remove(removed_id)

        self.processed_ids.append(message_id)
        self.processed_set.add(message_id)
        return True

    def generate_hash(self, content):
        """Generates a hash for content-based deduplication (when IDs are missing)."""
        # Mix in a rough timestamp (e.g. minute precision) if needed, but simple content hash
        # is risky if user says "hello" twice intentionally.
        # For UI inputs without IDs, we might rely on the fact that unintended duplicates
        # usually happen within milliseconds.
        return hashlib.sha256(str(content).encode('utf-8')).hexdigest()
