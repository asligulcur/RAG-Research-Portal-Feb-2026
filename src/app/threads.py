"""
Research Threads Management
Handles persistent storage and management of research threads
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from uuid import uuid4


class ThreadManager:
    """Manages research threads with persistent storage"""
    
    def __init__(self, storage_dir: str = "outputs/threads"):
        """
        Initialize thread manager.
        
        Args:
            storage_dir: Directory to store thread data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.threads_file = self.storage_dir / "threads.json"
        self._threads = None
    
    def _load_threads(self) -> Dict[str, Dict]:
        """Load threads from disk"""
        if self._threads is not None:
            return self._threads
        
        if self.threads_file.exists():
            try:
                with open(self.threads_file, 'r') as f:
                    self._threads = json.load(f)
            except Exception as e:
                print(f"Error loading threads: {e}")
                self._threads = {}
        else:
            self._threads = {}
        
        return self._threads
    
    def _save_threads(self):
        """Save threads to disk"""
        try:
            with open(self.threads_file, 'w') as f:
                json.dump(self._threads, f, indent=2)
        except Exception as e:
            print(f"Error saving threads: {e}")
    
    def create_thread(self, title: str, description: str = "") -> str:
        """
        Create a new research thread.
        
        Args:
            title: Thread title
            description: Optional thread description
            
        Returns:
            Thread ID
        """
        threads = self._load_threads()
        
        thread_id = str(uuid4())
        thread = {
            'id': thread_id,
            'title': title,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'queries': []
        }
        
        threads[thread_id] = thread
        self._threads = threads
        self._save_threads()
        
        return thread_id
    
    def get_thread(self, thread_id: str) -> Optional[Dict]:
        """Get a thread by ID"""
        threads = self._load_threads()
        return threads.get(thread_id)
    
    def get_all_threads(self) -> List[Dict]:
        """Get all threads, sorted by updated_at (most recent first)"""
        threads = self._load_threads()
        thread_list = list(threads.values())
        thread_list.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return thread_list
    
    def update_thread(self, thread_id: str, title: Optional[str] = None, 
                      description: Optional[str] = None):
        """Update thread metadata"""
        threads = self._load_threads()
        
        if thread_id not in threads:
            raise ValueError(f"Thread {thread_id} not found")
        
        thread = threads[thread_id]
        if title is not None:
            thread['title'] = title
        if description is not None:
            thread['description'] = description
        
        thread['updated_at'] = datetime.now().isoformat()
        self._threads = threads
        self._save_threads()
    
    def add_query_to_thread(self, thread_id: str, query: str, 
                           answer: str, citations: List[Dict], 
                           chunks: List[Dict], metadata: Optional[Dict] = None) -> Dict:
        """
        Add a query and its results to a thread.
        
        Args:
            thread_id: Thread ID
            query: User query
            answer: Generated answer
            citations: List of citations
            chunks: List of retrieved chunks
            metadata: Optional additional metadata
            
        Returns:
            Query entry dict
        """
        threads = self._load_threads()
        
        if thread_id not in threads:
            raise ValueError(f"Thread {thread_id} not found")
        
        thread = threads[thread_id]
        
        query_entry = {
            'id': str(uuid4()),
            'query': query,
            'answer': answer,
            'citations': citations,
            'chunks': chunks,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        
        thread['queries'].append(query_entry)
        thread['updated_at'] = datetime.now().isoformat()
        
        self._threads = threads
        self._save_threads()
        
        return query_entry
    
    def delete_thread(self, thread_id: str):
        """Delete a thread"""
        threads = self._load_threads()
        
        if thread_id in threads:
            del threads[thread_id]
            self._threads = threads
            self._save_threads()
    
    def delete_query_from_thread(self, thread_id: str, query_id: str):
        """Delete a query from a thread"""
        threads = self._load_threads()
        
        if thread_id not in threads:
            raise ValueError(f"Thread {thread_id} not found")
        
        thread = threads[thread_id]
        thread['queries'] = [q for q in thread['queries'] if q['id'] != query_id]
        thread['updated_at'] = datetime.now().isoformat()
        
        self._threads = threads
        self._save_threads()
    
    def get_thread_summary(self, thread_id: str) -> Dict:
        """Get summary statistics for a thread"""
        thread = self.get_thread(thread_id)
        if not thread:
            return {}
        
        queries = thread.get('queries', [])
        total_citations = sum(len(q.get('citations', [])) for q in queries)
        total_chunks = sum(len(q.get('chunks', [])) for q in queries)
        
        return {
            'thread_id': thread_id,
            'title': thread.get('title', 'Untitled'),
            'query_count': len(queries),
            'total_citations': total_citations,
            'total_chunks': total_chunks,
            'created_at': thread.get('created_at'),
            'updated_at': thread.get('updated_at')
        }
