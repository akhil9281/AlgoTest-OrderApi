"""
Write-Ahead Log (WAL) implementation for our crash recovery system.

in our WAL, we append all the logs for the state changes before they happen.
in case of a crash, the log can be replayed to restore system state.
"""

import json
import os
from typing import Any, Dict
from datetime import datetime


class WAL:
    """
    Write-Ahead Log implementation.
    
    Maintains an append-only log file with fsync() to guarantee system state is preserved.
    Each entry has:
    - LSN (Log Sequence Number): monotonically increasing ID
    - Timestamp: when the entry was created
    - Operation: INSERT, UPDATE, or DELETE
    - Table: ORDER or TRADE
    - Data: payload for the actual order/trade data
    """
    
    def __init__(self, file_path: str):
        """
        Initialize WAL.
        
        Args:
            file_path: Path to WAL file
        """
        self.file_path = file_path
        self.current_lsn = 0
        self.file_handle = None
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Open file in append mode
        self._open_file()
        
        # Determine current LSN from existing file, i.e. number of entries+1
        self._initialize_lsn()
    
    def _open_file(self):
        """open WAL file in 'a' append mode"""
        self.file_handle = open(self.file_path, 'a', buffering=1)
    
    def _initialize_lsn(self):
        """
        read existing WAL file to determine current LSN.
        LSN should be one more than the last entry.
        """
        if not os.path.exists(self.file_path) or os.path.getsize(self.file_path) == 0:
            self.current_lsn = 0
            return
        
        # Read file to find max LSN
        max_lsn = -1
        try:
            with open(self.file_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        lsn = entry.get('lsn', -1)
                        if lsn > max_lsn:
                            max_lsn = lsn
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading WAL file: {e}")
        
        self.current_lsn = max_lsn + 1
    
    def append(self, operation: str, table: str, data: Dict[str, Any]) -> int:
        """
        Append an entry to the WAL.
        
        Args:
            operation: Operation type (INSERT, UPDATE, DELETE)
            table: Table name (ORDER, TRADE)
            data: Data dictionary
            
        Returns:
            LSN of the appended entry
        """
        entry = {
            "lsn": self.current_lsn,
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "table": table,
            "data": data
        }
        
        # Write to file
        json_entry = json.dumps(entry)
        self.file_handle.write(json_entry + '\n')
        
        # Force write to disk (after every append to ensure no data-loss)
        self.file_handle.flush()
        os.fsync(self.file_handle.fileno())
        
        lsn = self.current_lsn
        self.current_lsn += 1
        
        return lsn
    
    def close(self):
        """Close the WAL file"""
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.flush()
            os.fsync(self.file_handle.fileno())
            self.file_handle.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def __del__(self):
        """Destructor - ensure file is closed"""
        self.close()
    
    def __repr__(self) -> str:
        """String representation"""
        return f"WAL(file={self.file_path}, current_lsn={self.current_lsn})"
