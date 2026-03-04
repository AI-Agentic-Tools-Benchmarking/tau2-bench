import sqlite3
import json
from collections.abc import MutableMapping, MutableSequence
from typing import TypeVar, Type, Iterator, Any, Union

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class DiskDict(MutableMapping):
    """A dictionary-like object backed by an SQLite database table."""
    
    def __init__(self, db_path: str, table_name: str, model_cls: Type[T]):
        self.db_path = db_path
        self.table_name = table_name
        self.model_cls = model_cls
        self._init_db()
        
    def _get_connection(self):
        # We use isolation_level=None for autocommit
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        # return rows as dictionaries for easier access if needed
        conn.row_factory = sqlite3.Row
        return conn
        
    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                f'''CREATE TABLE IF NOT EXISTS {self.table_name}
                   (id TEXT PRIMARY KEY,
                    data TEXT)'''
            )
            
    def __getitem__(self, key: str) -> T:
        with self._get_connection() as conn:
            cursor = conn.execute(f"SELECT data FROM {self.table_name} WHERE id = ?", (str(key),))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(key)
            # deserialize json to pydantic model
            return self.model_cls.model_validate_json(row['data'])
            
    def __setitem__(self, key: str, value: T) -> None:
        if not isinstance(value, BaseModel):
            raise TypeError("DiskDict values must be Pydantic BaseModels")
            
        data_str = value.model_dump_json()
        with self._get_connection() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {self.table_name} (id, data) VALUES (?, ?)", 
                (str(key), data_str)
            )
            
    def __delitem__(self, key: str) -> None:
        with self._get_connection() as conn:
            # Check if exists first to raise KeyError if missing
            cursor = conn.execute(f"SELECT 1 FROM {self.table_name} WHERE id = ?", (str(key),))
            if cursor.fetchone() is None:
                raise KeyError(key)
            conn.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (str(key),))
            
    def __iter__(self) -> Iterator[str]:
        with self._get_connection() as conn:
            cursor = conn.execute(f"SELECT id FROM {self.table_name}")
            for row in cursor:
                yield row['id']
                
    def __len__(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {self.table_name}")
            row = cursor.fetchone()
            return row['count']
            
    def clear(self) -> None:
        """Efficiently empty the table."""
        with self._get_connection() as conn:
            conn.execute(f"DELETE FROM {self.table_name}")
            
    def __contains__(self, key: Any) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(f"SELECT 1 FROM {self.table_name} WHERE id = ?", (str(key),))
            return cursor.fetchone() is not None


class DiskList(MutableSequence):
    """A list-like object backed by an SQLite database table."""
    
    def __init__(self, db_path: str, table_name: str, model_cls: Type[T]):
        self.db_path = db_path
        self.table_name = table_name
        self.model_cls = model_cls
        self._init_db()
        
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn
        
    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                f'''CREATE TABLE IF NOT EXISTS {self.table_name}
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT)'''
            )
            
    def __getitem__(self, i: Union[int, slice]) -> Union[T, list[T]]:
        if isinstance(i, slice):
            raise NotImplementedError("Slicing not supported on DiskList currently")
            
        with self._get_connection() as conn:
            if i < 0:
                count = len(self)
                i += count
            if i < 0:
                raise IndexError("list index out of range")
                
            cursor = conn.execute(f"SELECT data FROM {self.table_name} ORDER BY id LIMIT 1 OFFSET ?", (i,))
            row = cursor.fetchone()
            if row is None:
                raise IndexError("list index out of range")
            return self.model_cls.model_validate_json(row['data'])
            
    def __setitem__(self, i: Union[int, slice], value: T) -> None:
        if isinstance(i, slice):
            raise NotImplementedError("Slicing not supported on DiskList currently")
        if not isinstance(value, BaseModel):
            raise TypeError("DiskList values must be Pydantic BaseModels")
            
        data_str = value.model_dump_json()
        with self._get_connection() as conn:
            if i < 0:
                count = len(self)
                i += count
            
            # Find the ID of the row at offset i
            cursor = conn.execute(f"SELECT id FROM {self.table_name} ORDER BY id LIMIT 1 OFFSET ?", (i,))
            row = cursor.fetchone()
            if row is None:
                raise IndexError("list assignment index out of range")
            row_id = row['id']
            
            conn.execute(
                f"UPDATE {self.table_name} SET data = ? WHERE id = ?", 
                (data_str, row_id)
            )
            
    def __delitem__(self, i: Union[int, slice]) -> None:
        if isinstance(i, slice):
            raise NotImplementedError("Slicing not supported on DiskList currently")
            
        with self._get_connection() as conn:
            if i < 0:
                count = len(self)
                i += count
            
            # Find the ID of the row at offset i
            cursor = conn.execute(f"SELECT id FROM {self.table_name} ORDER BY id LIMIT 1 OFFSET ?", (i,))
            row = cursor.fetchone()
            if row is None:
                raise IndexError("list assignment index out of range")
            row_id = row['id']
            
            conn.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (row_id,))
            
    def insert(self, i: int, value: T) -> None:
        if not isinstance(value, BaseModel):
            raise TypeError("DiskList values must be Pydantic BaseModels")
            
        data_str = value.model_dump_json()
        with self._get_connection() as conn:
            count = len(self)
            if i < 0:
                i += count
            i = max(0, min(i, count))
            
            if i == count:
                # Just append
                conn.execute(f"INSERT INTO {self.table_name} (data) VALUES (?)", (data_str,))
            else:
                raise NotImplementedError("Inserting in the middle of DiskList is not supported. Use append.")
                
    def append(self, value: T) -> None:
        if not isinstance(value, BaseModel):
            raise TypeError("DiskList values must be Pydantic BaseModels")
            
        data_str = value.model_dump_json()
        with self._get_connection() as conn:
            conn.execute(f"INSERT INTO {self.table_name} (data) VALUES (?)", (data_str,))
            
    def __len__(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {self.table_name}")
            row = cursor.fetchone()
            return row['count']
            
    def clear(self) -> None:
        with self._get_connection() as conn:
            conn.execute(f"DELETE FROM {self.table_name}")
            
    def __iter__(self) -> Iterator[T]:
        with self._get_connection() as conn:
            cursor = conn.execute(f"SELECT data FROM {self.table_name} ORDER BY id")
            for row in cursor:
                yield self.model_cls.model_validate_json(row['data'])
