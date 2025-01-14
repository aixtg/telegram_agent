from repo.dbhelper import MongoHelper
from typing import Any, Dict, List, Optional


class UserRepository(MongoHelper):
    def __init__(self, db_name: str = 'mydb', collection_name: str = 'users'):
        super().__init__(db_name, collection_name)

    def find_by_tg_id(self, tg_id: int) -> Optional[Dict[str, Any]]:
        """Find a user by tg_id."""
        return self.find_one({'tg_id': tg_id})

    def initiate_doc(self, tg_id: int):
        """save a user by tg_id."""
        return  self.update_one({'tg_id' : tg_id},
                                {'tg_id' : tg_id, 'status' : 'started'},
                                True)