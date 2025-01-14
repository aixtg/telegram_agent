from pymongo import MongoClient
from pymongo.collection import Collection
from typing import Any, Dict, List, Optional


class MongoHelper:
    def __init__(self, db_name: str, collection_name: str, host: str = 'localhost', port: int = 27017):
        self.client = MongoClient(host, port)
        self.db = self.client[db_name]
        self.collection: Collection = self.db[collection_name]

    def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert a single document into the collection."""
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple documents into the collection."""
        result = self.collection.insert_many(documents)
        return [str(id) for id in result.inserted_ids]

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find one document based on the query."""
        return self.collection.find_one(query)

    def find_all(self, query: Dict[str, Any] = {}, limit: int = 0) -> List[Dict[str, Any]]:
        """Find multiple documents matching the query."""
        cursor = self.collection.find(query).limit(limit)
        return list(cursor)

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool) -> bool:
        """Update a single document based on the query."""
        result = self.collection.update_one(query, {'$set': update})
        return result.modified_count > 0

    def update_many(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """Update multiple documents matching the query."""
        result = self.collection.update_many(query, {'$set': update})
        return result.modified_count

    def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete a single document based on the query."""
        result = self.collection.delete_one(query)
        return result.deleted_count > 0

    def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents matching the query."""
        result = self.collection.delete_many(query)
        return result.deleted_count

    def count_documents(self, query: Dict[str, Any] = {}) -> int:
        """Count the number of documents that match the query."""
        return self.collection.count_documents(query)

    def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run an aggregation pipeline."""
        return list(self.collection.aggregate(pipeline))

    def close(self):
        """Close the MongoDB connection."""
        self.client.close()
