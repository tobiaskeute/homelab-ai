"""
Monica client that connects to the Monica REST API.

Provides LangGraph-compatible tools for integrating Monica CRM via its REST API.
Inspired by and compatible with the tools from https://github.com/Jacob-Stokes/monica-mcp
"""
import logging
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

class MonicaClient:
    """
    Client for Monica CRM REST API.
    
    Provides low-level API access to Monica.
    """
    
    def __init__(self, base_url: str, api_token: str):
        """
        Initialize the Monica client.
        
        Args:
            base_url: The base URL of the Monica instance (e.g., http://localhost:8093)
            api_token: The API token for authentication (Bearer token)
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_token}"},
            timeout=30.0
        )
    
    # ==================== Contact Methods ====================
    
    async def list_contacts(
        self,
        limit: int = 10,
        page: int = 1,
        sort: str = "-created_at",
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """List contacts from Monica."""
        params = {"limit": min(limit, 100), "page": page, "sort": sort}
        if query:
            params["query"] = query
        response = await self._client.get("/api/contacts", params=params)
        response.raise_for_status()
        return response.json()
    
    async def search_contacts(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for contacts by name, email, or other fields."""
        params = {"query": query, "limit": min(limit, 100)}
        response = await self._client.get("/api/contacts", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_contact(self, contact_id: int) -> Dict[str, Any]:
        """Get details of a specific contact by ID."""
        response = await self._client.get(f"/api/contacts/{contact_id}")
        response.raise_for_status()
        return response.json()
    
    async def create_contact(
        self,
        first_name: str,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        birthday: Optional[str] = None,
        address: Optional[str] = None,
        description: Optional[str] = None,
        company: Optional[str] = None,
        job: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new contact in Monica."""
        # Monica requires these three fields
        data = {
            "first_name": first_name,
            "is_birthdate_known": False,
            "is_deceased": False,
            "is_deceased_date_known": False
        }
        if last_name:
            data["last_name"] = last_name
        if email:
            data["email"] = [{"address": email}]
        if phone:
            data["phone"] = [{"number": phone}]
        if birthday:
            # Monica expects birthdate_day, birthdate_month, birthdate_year as integers
            # Parse YYYY-MM-DD format
            try:
                parts = birthday.split('-')
                if len(parts) == 3:
                    data["birthdate_year"] = int(parts[0])
                    data["birthdate_month"] = int(parts[1])
                    data["birthdate_day"] = int(parts[2])
                    data["is_birthdate_known"] = True
                elif len(parts) == 2:
                    # MM-DD format (year unknown)
                    data["birthdate_month"] = int(parts[0])
                    data["birthdate_day"] = int(parts[1])
                    data["is_birthdate_known"] = True
            except (ValueError, AttributeError):
                # If birthday format is invalid, don't set it
                pass
        if address:
            data["address"] = address
        if description:
            data["description"] = description
        if company:
            data["company"] = company
        if job:
            data["job"] = job
        response = await self._client.post("/api/contacts", json=data)
        response.raise_for_status()
        return response.json()
    
    async def update_contact(
        self,
        contact_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        birthday: Optional[str] = None,
        address: Optional[str] = None,
        description: Optional[str] = None,
        company: Optional[str] = None,
        job: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing contact in Monica."""
        data: Dict[str, Any] = {}
        if first_name is not None:
            data["first_name"] = first_name
        if last_name is not None:
            data["last_name"] = last_name
        if email is not None:
            data["email"] = [{"address": email}]
        if phone is not None:
            data["phone"] = [{"number": phone}]
        if birthday is not None:
            # Monica expects birthdate_day, birthdate_month, birthdate_year as integers
            try:
                parts = birthday.split('-')
                if len(parts) == 3:
                    data["birthdate_year"] = int(parts[0])
                    data["birthdate_month"] = int(parts[1])
                    data["birthdate_day"] = int(parts[2])
                    data["is_birthdate_known"] = True
                elif len(parts) == 2:
                    data["birthdate_month"] = int(parts[0])
                    data["birthdate_day"] = int(parts[1])
                    data["is_birthdate_known"] = True
            except (ValueError, AttributeError):
                pass
        if address is not None:
            data["address"] = address
        if description is not None:
            data["description"] = description
        if company is not None:
            data["company"] = company
        if job is not None:
            data["job"] = job
        if not data:
            return {"error": "No fields to update"}
        response = await self._client.put(f"/api/contacts/{contact_id}", json=data)
        response.raise_for_status()
        return response.json()
    
    async def delete_contact(self, contact_id: int, confirm: bool = False) -> Dict[str, Any]:
        """Delete a contact from Monica."""
        if not confirm:
            return {"error": "confirm must be true to delete"}
        response = await self._client.delete(f"/api/contacts/{contact_id}")
        response.raise_for_status()
        return {"status": "deleted", "contact_id": contact_id}
    
    # ==================== Contact Field Methods ====================
    
    async def list_contact_fields(self, contact_id: int) -> List[Dict[str, Any]]:
        """List contact fields for a contact."""
        response = await self._client.get(f"/api/contacts/{contact_id}/contactfields")
        response.raise_for_status()
        return response.json().get("data", [])
    
    async def add_contact_field(
        self,
        contact_id: int,
        field_type: str,
        value: str
    ) -> Dict[str, Any]:
        """Add a contact field (email, phone, social, etc.)."""
        # First get the field type ID
        field_types = await self.list_contact_field_types()
        field_type_obj = next(
            (ft for ft in field_types if ft.get("name", "").lower() == field_type.lower()),
            None
        )
        if not field_type_obj:
            return {"error": f"Field type '{field_type}' not found"}
        
        data = {
            "contact_id": contact_id,
            "contact_field_type_id": field_type_obj["id"],
            "data": value
        }
        response = await self._client.post("/api/contactfields", json=data)
        response.raise_for_status()
        return response.json()
    
    async def list_contact_field_types(self) -> List[Dict[str, Any]]:
        """List available contact field types."""
        response = await self._client.get("/api/contactfieldtypes")
        response.raise_for_status()
        return response.json().get("data", [])
    
    # ==================== Address Methods ====================
    
    async def list_addresses(self, contact_id: int) -> List[Dict[str, Any]]:
        """List addresses for a contact."""
        response = await self._client.get(f"/api/contacts/{contact_id}/addresses")
        response.raise_for_status()
        return response.json().get("data", [])
    
    async def add_address(
        self,
        contact_id: int,
        name: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        province: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add an address to a contact."""
        # Get country ID
        country_id = None
        if country:
            countries = await self.list_countries()
            country_obj = next(
                (c for c in countries if c.get("name", "").lower() == country.lower() or c.get("iso", "").lower() == country.lower()),
                None
            )
            if country_obj:
                country_id = country_obj["id"]
        
        data = {
            "contact_id": contact_id,
        }
        if name:
            data["name"] = name
        if street:
            data["street"] = street
        if city:
            data["city"] = city
        if province:
            data["province"] = province
        if postal_code:
            data["postal_code"] = postal_code
        if country_id:
            data["country_id"] = country_id
        
        response = await self._client.post("/api/addresses", json=data)
        response.raise_for_status()
        return response.json()
    
    async def list_countries(self) -> List[Dict[str, Any]]:
        """List available countries."""
        response = await self._client.get("/api/countries")
        response.raise_for_status()
        return response.json().get("data", [])
    
    # ==================== Tag Methods ====================
    
    async def list_tags(self, limit: int = 50, page: int = 1) -> Dict[str, Any]:
        """List all tags from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        response = await self._client.get("/api/tags", params=params)
        response.raise_for_status()
        return response.json()
    
    async def add_tag_to_contact(self, contact_id: int, tag_name: str) -> Dict[str, Any]:
        """Add a tag to a contact in Monica."""
        data = {"name": tag_name}
        response = await self._client.post(
            f"/api/contacts/{contact_id}/tags",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def remove_tag_from_contact(self, contact_id: int, tag_name: str) -> Dict[str, Any]:
        """Remove a tag from a contact."""
        # First get the tag ID
        tags = await self.list_tags(limit=100)
        tag_obj = next(
            (t for t in tags.get("data", []) if t.get("name", "").lower() == tag_name.lower()),
            None
        )
        if not tag_obj:
            return {"error": f"Tag '{tag_name}' not found"}
        
        response = await self._client.post(
            f"/api/contacts/{contact_id}/unsetTag",
            json={"tags": [tag_obj["id"]]}
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== Relationship Methods ====================
    
    async def list_relationships(self, contact_id: int) -> List[Dict[str, Any]]:
        """List relationships for a contact."""
        response = await self._client.get(f"/api/contacts/{contact_id}/relationships")
        response.raise_for_status()
        return response.json().get("data", [])
    
    async def add_relationship(
        self,
        contact_id: int,
        related_contact_id: int,
        relationship_type: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a relationship between contacts.
        
        Monica expects:
        - contact_is (not contact_id)
        - of_contact (not related_contact_id)
        - relationship_type_id
        """
        # Get relationship type ID
        rel_types = await self.list_relationship_types()
        rel_type_obj = next(
            (rt for rt in rel_types if rt.get("name", "").lower() == relationship_type.lower()),
            None
        )
        if not rel_type_obj:
            return {"error": f"Relationship type '{relationship_type}' not found"}
        
        data = {
            "contact_is": contact_id,
            "of_contact": related_contact_id,
            "relationship_type_id": rel_type_obj["id"],
        }
        if description:
            data["description"] = description
        
        response = await self._client.post("/api/relationships", json=data)
        response.raise_for_status()
        return response.json()
    
    async def list_relationship_types(self) -> List[Dict[str, Any]]:
        """List available relationship types."""
        response = await self._client.get("/api/relationshiptypes")
        response.raise_for_status()
        return response.json().get("data", [])
    
    # ==================== Note Methods ====================
    
    async def list_notes(
        self,
        contact_id: Optional[int] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict[str, Any]:
        """List notes from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/notes", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_note(
        self,
        content: str,
        contact_id: Optional[int] = None,
        title: Optional[str] = None,
        is_favorite: bool = False
    ) -> Dict[str, Any]:
        """Create a new note in Monica."""
        data = {"content": content}
        if contact_id:
            data["contact_id"] = contact_id
        if title:
            data["title"] = title
        if is_favorite:
            data["is_favorite"] = is_favorite
        response = await self._client.post("/api/notes", json=data)
        response.raise_for_status()
        return response.json()
    
    async def delete_note(self, note_id: int, confirm: bool = False) -> Dict[str, Any]:
        """Delete a note."""
        if not confirm:
            return {"error": "confirm must be true to delete"}
        response = await self._client.delete(f"/api/notes/{note_id}")
        response.raise_for_status()
        return {"status": "deleted", "note_id": note_id}
    
    # ==================== Activity Methods ====================
    
    async def list_activities(
        self,
        limit: int = 10,
        page: int = 1,
        contact_id: Optional[int] = None,
        sort: str = "-created_at"
    ) -> Dict[str, Any]:
        """List activities from Monica."""
        params = {"limit": min(limit, 100), "page": page, "sort": sort}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/activities", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_activity(
        self,
        content: str,
        contact_id: Optional[int] = None,
        activity_type: str = "Note",
        date: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new activity in Monica."""
        # Get activity type ID
        activity_types = await self.list_activity_types()
        activity_type_obj = next(
            (at for at in activity_types if at.get("name", "").lower() == activity_type.lower()),
            None
        )
        if not activity_type_obj:
            return {"error": f"Activity type '{activity_type}' not found"}
        
        # Monica requires: summary, happened_at, contacts
        data: Dict[str, Any] = {
            "summary": content,
            "activity_type_id": activity_type_obj["id"],
        }
        if date:
            data["happened_at"] = date
        if contact_id:
            data["contacts"] = [{"contact_id": contact_id}]
        if description:
            data["description"] = description
        response = await self._client.post("/api/activities", json=data)
        response.raise_for_status()
        return response.json()
    
    async def list_activity_types(self) -> List[Dict[str, Any]]:
        """List available activity types."""
        response = await self._client.get("/api/activitytypes")
        response.raise_for_status()
        return response.json().get("data", [])
    
    # ==================== Call Methods ====================
    
    async def list_calls(
        self,
        contact_id: Optional[int] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict[str, Any]:
        """List calls from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/calls", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_call(
        self,
        content: str,
        contact_id: Optional[int] = None,
        date: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new call record in Monica."""
        data = {"content": content}
        if contact_id:
            data["contact_id"] = contact_id
        if date:
            # Monica expects called_at, not date
            data["called_at"] = date
        if description:
            data["description"] = description
        response = await self._client.post("/api/calls", json=data)
        response.raise_for_status()
        return response.json()
    
    # ==================== Conversation Methods ====================
    
    async def list_conversations(
        self,
        contact_id: Optional[int] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict[str, Any]:
        """List conversations from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/conversations", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_conversation(
        self,
        content: str,
        contact_id: Optional[int] = None,
        date: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new conversation in Monica."""
        data = {"content": content}
        if contact_id:
            data["contact_id"] = contact_id
        if date:
            # Monica expects happened_at, not date
            data["happened_at"] = date
        if description:
            data["description"] = description
        response = await self._client.post("/api/conversations", json=data)
        response.raise_for_status()
        return response.json()
    
    # ==================== Reminder Methods ====================
    
    async def list_reminders(
        self,
        contact_id: Optional[int] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict[str, Any]:
        """List reminders from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/reminders", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_reminder(
        self,
        title: str,
        date: str,
        contact_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new reminder in Monica."""
        # Monica expects initial_date, not date
        data = {"title": title, "initial_date": date}
        if contact_id:
            data["contact_id"] = contact_id
        if description:
            data["description"] = description
        response = await self._client.post("/api/reminders", json=data)
        response.raise_for_status()
        return response.json()
    
    # ==================== Task Methods ====================
    
    async def list_tasks(
        self,
        contact_id: Optional[int] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict[str, Any]:
        """List tasks from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/tasks", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_task(
        self,
        title: str,
        contact_id: Optional[int] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        is_completed: bool = False
    ) -> Dict[str, Any]:
        """Create a new task in Monica."""
        data = {"title": title}
        if contact_id:
            data["contact_id"] = contact_id
        if description:
            data["description"] = description
        if due_date:
            data["due_date"] = due_date
        if is_completed:
            data["is_completed"] = is_completed
        response = await self._client.post("/api/tasks", json=data)
        response.raise_for_status()
        return response.json()
    
    async def complete_task(self, task_id: int) -> Dict[str, Any]:
        """Mark a task as completed."""
        response = await self._client.post(f"/api/tasks/{task_id}/complete")
        response.raise_for_status()
        return response.json()
    
    # ==================== Gift Methods ====================
    
    async def list_gifts(
        self,
        contact_id: Optional[int] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict[str, Any]:
        """List gifts from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/gifts", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_gift(
        self,
        title: str,
        date: str,
        contact_id: Optional[int] = None,
        description: Optional[str] = None,
        budget: Optional[float] = None,
        status: str = "idea"
    ) -> Dict[str, Any]:
        """Create a new gift in Monica."""
        # Monica expects 'name' not 'title', and 'status' is required
        data = {"name": title, "date": date, "status": status}
        if contact_id:
            data["contact_id"] = contact_id
        if description:
            data["comment"] = description  # Monica uses 'comment' not 'description'
        if budget:
            data["amount"] = budget  # Monica uses 'amount' not 'budget'
        response = await self._client.post("/api/gifts", json=data)
        response.raise_for_status()
        return response.json()
    
    # ==================== Debt Methods ====================
    
    async def list_debts(
        self,
        contact_id: Optional[int] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict[str, Any]:
        """List debts from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/debts", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_debt(
        self,
        reason: str,
        amount: float,
        date: str,
        contact_id: Optional[int] = None,
        description: Optional[str] = None,
        in_debt: bool = True
    ) -> Dict[str, Any]:
        """Create a new debt in Monica.
        
        Monica expects:
        - reason (not title)
        - amount
        - date
        - in_debt as string "yes" or "no" (not boolean is_in_debt)
        - status (required: "inprogress" or "completed")
        """
        data = {
            "reason": reason,
            "amount": amount,
            "date": date,
            "in_debt": "yes" if in_debt else "no",
            "status": "inprogress"
        }
        if contact_id:
            data["contact_id"] = contact_id
        if description:
            data["description"] = description
        response = await self._client.post("/api/debts", json=data)
        response.raise_for_status()
        return response.json()
    
    # ==================== Journal Methods ====================
    
    async def list_journals(
        self,
        contact_id: Optional[int] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict[str, Any]:
        """List journal entries from Monica."""
        params = {"limit": min(limit, 100), "page": page}
        if contact_id:
            params["contact_id"] = contact_id
        response = await self._client.get("/api/journals", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_journal(
        self,
        title: str,
        date: str,
        content: str,
        contact_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new journal entry in Monica."""
        data = {"title": title, "date": date, "content": content}
        if contact_id:
            data["contact_id"] = contact_id
        response = await self._client.post("/api/journals", json=data)
        response.raise_for_status()
        return response.json()
    
    # ==================== Reference Data Methods ====================
    
    async def list_genders(self) -> List[Dict[str, Any]]:
        """List available genders."""
        response = await self._client.get("/api/genders")
        response.raise_for_status()
        return response.json().get("data", [])
    
    async def list_currencies(self) -> List[Dict[str, Any]]:
        """List available currencies."""
        response = await self._client.get("/api/currencies")
        response.raise_for_status()
        return response.json().get("data", [])
    
    # ==================== Utility Methods ====================
    
    async def get_me(self) -> Dict[str, Any]:
        """Get current user information."""
        response = await self._client.get("/api/me")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class MonicaAdapter:
    """
    Adapter for Monica CRM that provides LangGraph-compatible tools.
    
    This adapter wraps the MonicaClient and exposes its methods as
    LangChain-compatible tools that can be used with agents.
    
    Provides tools compatible with the Jacob-Stokes/monica-mcp server.
    """
    
    def __init__(self, base_url: str, api_token: str):
        """
        Initialize the Monica adapter.
        
        Args:
            base_url: The base URL of the Monica instance
            api_token: The API token for authentication
        """
        self.client = MonicaClient(base_url=base_url, api_token=api_token)
        
        # Create tools as instance attributes
        self.list_contacts_tool = self._create_list_contacts_tool()
        self.search_contacts_tool = self._create_search_contacts_tool()
        self.get_contact_tool = self._create_get_contact_tool()
        self.create_contact_tool = self._create_create_contact_tool()
        self.update_contact_tool = self._create_update_contact_tool()
        self.delete_contact_tool = self._create_delete_contact_tool()
        
        # Contact fields, addresses, tags
        self.list_contact_fields_tool = self._create_list_contact_fields_tool()
        self.add_contact_field_tool = self._create_add_contact_field_tool()
        self.list_contact_field_types_tool = self._create_list_contact_field_types_tool()
        self.list_addresses_tool = self._create_list_addresses_tool()
        self.add_address_tool = self._create_add_address_tool()
        self.list_countries_tool = self._create_list_countries_tool()
        self.list_tags_tool = self._create_list_tags_tool()
        self.add_tag_to_contact_tool = self._create_add_tag_to_contact_tool()
        self.remove_tag_from_contact_tool = self._create_remove_tag_from_contact_tool()
        
        # Relationships
        self.list_relationships_tool = self._create_list_relationships_tool()
        self.add_relationship_tool = self._create_add_relationship_tool()
        self.list_relationship_types_tool = self._create_list_relationship_types_tool()
        
        # Notes
        self.list_notes_tool = self._create_list_notes_tool()
        self.create_note_tool = self._create_create_note_tool()
        self.delete_note_tool = self._create_delete_note_tool()
        
        # Activities
        self.list_activities_tool = self._create_list_activities_tool()
        self.create_activity_tool = self._create_create_activity_tool()
        self.list_activity_types_tool = self._create_list_activity_types_tool()
        
        # Calls
        self.list_calls_tool = self._create_list_calls_tool()
        self.create_call_tool = self._create_create_call_tool()
        
        # Conversations
        self.list_conversations_tool = self._create_list_conversations_tool()
        self.create_conversation_tool = self._create_create_conversation_tool()
        
        # Reminders
        self.list_reminders_tool = self._create_list_reminders_tool()
        self.create_reminder_tool = self._create_create_reminder_tool()
        
        # Tasks
        self.list_tasks_tool = self._create_list_tasks_tool()
        self.create_task_tool = self._create_create_task_tool()
        self.complete_task_tool = self._create_complete_task_tool()
        
        # Gifts
        self.list_gifts_tool = self._create_list_gifts_tool()
        self.create_gift_tool = self._create_create_gift_tool()
        
        # Debts
        self.list_debts_tool = self._create_list_debts_tool()
        self.create_debt_tool = self._create_create_debt_tool()
        
        # Journals
        self.list_journals_tool = self._create_list_journals_tool()
        self.create_journal_tool = self._create_create_journal_tool()
        
        # Reference data
        self.list_genders_tool = self._create_list_genders_tool()
        self.list_currencies_tool = self._create_list_currencies_tool()
        
        # Build tools list - all prefixed with monica_ for clarity
        self._tools = [
            # Contacts
            self.list_contacts_tool,
            self.search_contacts_tool,
            self.get_contact_tool,
            self.create_contact_tool,
            self.update_contact_tool,
            self.delete_contact_tool,
            # Contact details
            self.list_contact_fields_tool,
            self.add_contact_field_tool,
            self.list_contact_field_types_tool,
            self.list_addresses_tool,
            self.add_address_tool,
            self.list_countries_tool,
            self.list_tags_tool,
            self.add_tag_to_contact_tool,
            self.remove_tag_from_contact_tool,
            # Relationships
            self.list_relationships_tool,
            self.add_relationship_tool,
            self.list_relationship_types_tool,
            # Notes
            self.list_notes_tool,
            self.create_note_tool,
            self.delete_note_tool,
            # Activities
            self.list_activities_tool,
            self.create_activity_tool,
            self.list_activity_types_tool,
            # Calls
            self.list_calls_tool,
            self.create_call_tool,
            # Conversations
            self.list_conversations_tool,
            self.create_conversation_tool,
            # Reminders
            self.list_reminders_tool,
            self.create_reminder_tool,
            # Tasks
            self.list_tasks_tool,
            self.create_task_tool,
            self.complete_task_tool,
            # Gifts
            self.list_gifts_tool,
            self.create_gift_tool,
            # Debts
            self.list_debts_tool,
            self.create_debt_tool,
            # Journals
            self.list_journals_tool,
            self.create_journal_tool,
            # Reference
            self.list_genders_tool,
            self.list_currencies_tool,
        ]
    
    # ==================== Tool Factories ====================
    
    def _create_list_contacts_tool(self):
        @tool
        async def list_contacts(limit: int = 10, page: int = 1, sort: str = "-created_at", query: Optional[str] = None) -> Dict[str, Any]:
            """List contacts from Monica CRM."""
            return await self.client.list_contacts(limit=limit, page=page, sort=sort, query=query)
        return list_contacts
    
    def _create_search_contacts_tool(self):
        @tool
        async def search_contacts(query: str, limit: int = 10) -> Dict[str, Any]:
            """Search for contacts by name, email, or other fields."""
            return await self.client.search_contacts(query=query, limit=limit)
        return search_contacts
    
    def _create_get_contact_tool(self):
        @tool
        async def get_contact(contact_id: int) -> Dict[str, Any]:
            """Get details of a specific contact by ID."""
            return await self.client.get_contact(contact_id=contact_id)
        return get_contact
    
    def _create_create_contact_tool(self):
        @tool
        async def create_contact(
            first_name: str,
            last_name: Optional[str] = None,
            email: Optional[str] = None,
            phone: Optional[str] = None,
            birthday: Optional[str] = None,
            address: Optional[str] = None,
            description: Optional[str] = None,
            company: Optional[str] = None,
            job: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new contact in Monica CRM. 
            
            Use this to add people to your contacts. 
            Example: first_name='John', last_name='Doe' creates a contact named 'John Doe'.
            Only first_name is required; all other fields are optional.
            """
            return await self.client.create_contact(
                first_name=first_name, last_name=last_name, email=email,
                phone=phone, birthday=birthday, address=address,
                description=description, company=company, job=job
            )
        return create_contact
    
    def _create_update_contact_tool(self):
        @tool
        async def update_contact(
            contact_id: int,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            email: Optional[str] = None,
            phone: Optional[str] = None,
            birthday: Optional[str] = None,
            address: Optional[str] = None,
            description: Optional[str] = None,
            company: Optional[str] = None,
            job: Optional[str] = None
        ) -> Dict[str, Any]:
            """Update an existing contact in Monica."""
            return await self.client.update_contact(
                contact_id=contact_id, first_name=first_name, last_name=last_name,
                email=email, phone=phone, birthday=birthday, address=address,
                description=description, company=company, job=job
            )
        return update_contact
    
    def _create_delete_contact_tool(self):
        @tool
        async def delete_contact(contact_id: int, confirm: bool = False) -> Dict[str, Any]:
            """Delete a contact from Monica. Requires confirm=true."""
            if not confirm:
                return {"error": "confirm must be true to delete"}
            return await self.client.delete_contact(contact_id=contact_id, confirm=confirm)
        return delete_contact
    
    def _create_list_contact_fields_tool(self):
        @tool
        async def list_contact_fields(contact_id: int) -> List[Dict[str, Any]]:
            """List contact fields for a contact."""
            return await self.client.list_contact_fields(contact_id=contact_id)
        return list_contact_fields
    
    def _create_add_contact_field_tool(self):
        @tool
        async def add_contact_field(contact_id: int, field_type: str, value: str) -> Dict[str, Any]:
            """Add a contact field (email, phone, social, etc.) to a contact."""
            return await self.client.add_contact_field(
                contact_id=contact_id, field_type=field_type, value=value
            )
        return add_contact_field
    
    def _create_list_contact_field_types_tool(self):
        @tool
        async def list_contact_field_types() -> List[Dict[str, Any]]:
            """List available contact field types."""
            return await self.client.list_contact_field_types()
        return list_contact_field_types
    
    def _create_list_addresses_tool(self):
        @tool
        async def list_addresses(contact_id: int) -> List[Dict[str, Any]]:
            """List addresses for a contact."""
            return await self.client.list_addresses(contact_id=contact_id)
        return list_addresses
    
    def _create_add_address_tool(self):
        @tool
        async def add_address(
            contact_id: int,
            name: Optional[str] = None,
            street: Optional[str] = None,
            city: Optional[str] = None,
            province: Optional[str] = None,
            postal_code: Optional[str] = None,
            country: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add an address to a contact."""
            return await self.client.add_address(
                contact_id=contact_id, name=name, street=street, city=city,
                province=province, postal_code=postal_code, country=country
            )
        return add_address
    
    def _create_list_countries_tool(self):
        @tool
        async def list_countries() -> List[Dict[str, Any]]:
            """List available countries."""
            return await self.client.list_countries()
        return list_countries
    
    def _create_list_tags_tool(self):
        @tool
        async def list_tags(limit: int = 50, page: int = 1) -> Dict[str, Any]:
            """List all tags from Monica."""
            return await self.client.list_tags(limit=limit, page=page)
        return list_tags
    
    def _create_add_tag_to_contact_tool(self):
        @tool
        async def add_tag_to_contact(contact_id: int, tag_name: str) -> Dict[str, Any]:
            """Add a tag to a contact in Monica."""
            return await self.client.add_tag_to_contact(contact_id=contact_id, tag_name=tag_name)
        return add_tag_to_contact
    
    def _create_remove_tag_from_contact_tool(self):
        @tool
        async def remove_tag_from_contact(contact_id: int, tag_name: str) -> Dict[str, Any]:
            """Remove a tag from a contact."""
            return await self.client.remove_tag_from_contact(contact_id=contact_id, tag_name=tag_name)
        return remove_tag_from_contact
    
    def _create_list_relationships_tool(self):
        @tool
        async def list_relationships(contact_id: int) -> List[Dict[str, Any]]:
            """List relationships for a contact."""
            return await self.client.list_relationships(contact_id=contact_id)
        return list_relationships
    
    def _create_add_relationship_tool(self):
        @tool
        async def add_relationship(
            contact_id: int,
            related_contact_id: int,
            relationship_type: str,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add a relationship between contacts."""
            return await self.client.add_relationship(
                contact_id=contact_id, related_contact_id=related_contact_id,
                relationship_type=relationship_type, description=description
            )
        return add_relationship
    
    def _create_list_relationship_types_tool(self):
        @tool
        async def list_relationship_types() -> List[Dict[str, Any]]:
            """List available relationship types."""
            return await self.client.list_relationship_types()
        return list_relationship_types
    
    def _create_list_notes_tool(self):
        @tool
        async def list_notes(contact_id: Optional[int] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
            """List notes from Monica."""
            return await self.client.list_notes(contact_id=contact_id, limit=limit, page=page)
        return list_notes
    
    def _create_create_note_tool(self):
        @tool
        async def create_note(
            content: str,
            contact_id: Optional[int] = None,
            title: Optional[str] = None,
            is_favorite: bool = False
        ) -> Dict[str, Any]:
            """Create a new note in Monica."""
            return await self.client.create_note(
                content=content, contact_id=contact_id, title=title, is_favorite=is_favorite
            )
        return create_note
    
    def _create_delete_note_tool(self):
        @tool
        async def delete_note(note_id: int, confirm: bool = False) -> Dict[str, Any]:
            """Delete a note. Requires confirm=true."""
            if not confirm:
                return {"error": "confirm must be true to delete"}
            return await self.client.delete_note(note_id=note_id, confirm=confirm)
        return delete_note
    
    def _create_list_activities_tool(self):
        @tool
        async def list_activities(limit: int = 10, page: int = 1, contact_id: Optional[int] = None, sort: str = "-created_at") -> Dict[str, Any]:
            """List activities from Monica."""
            return await self.client.list_activities(limit=limit, page=page, contact_id=contact_id, sort=sort)
        return list_activities
    
    def _create_create_activity_tool(self):
        @tool
        async def create_activity(
            content: str,
            contact_id: Optional[int] = None,
            activity_type: str = "Note",
            date: Optional[str] = None,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new activity in Monica."""
            return await self.client.create_activity(
                content=content, contact_id=contact_id, activity_type=activity_type,
                date=date, description=description
            )
        return create_activity
    
    def _create_list_activity_types_tool(self):
        @tool
        async def list_activity_types() -> List[Dict[str, Any]]:
            """List available activity types."""
            return await self.client.list_activity_types()
        return list_activity_types
    
    def _create_list_calls_tool(self):
        @tool
        async def list_calls(contact_id: Optional[int] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
            """List calls from Monica."""
            return await self.client.list_calls(contact_id=contact_id, limit=limit, page=page)
        return list_calls
    
    def _create_create_call_tool(self):
        @tool
        async def create_call(
            content: str,
            contact_id: Optional[int] = None,
            date: Optional[str] = None,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new call record in Monica."""
            return await self.client.create_call(
                content=content, contact_id=contact_id, date=date, description=description
            )
        return create_call
    
    def _create_list_conversations_tool(self):
        @tool
        async def list_conversations(contact_id: Optional[int] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
            """List conversations from Monica."""
            return await self.client.list_conversations(contact_id=contact_id, limit=limit, page=page)
        return list_conversations
    
    def _create_create_conversation_tool(self):
        @tool
        async def create_conversation(
            content: str,
            contact_id: Optional[int] = None,
            date: Optional[str] = None,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new conversation in Monica."""
            return await self.client.create_conversation(
                content=content, contact_id=contact_id, date=date, description=description
            )
        return create_conversation
    
    def _create_list_reminders_tool(self):
        @tool
        async def list_reminders(contact_id: Optional[int] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
            """List reminders from Monica."""
            return await self.client.list_reminders(contact_id=contact_id, limit=limit, page=page)
        return list_reminders
    
    def _create_create_reminder_tool(self):
        @tool
        async def create_reminder(
            title: str,
            date: str,
            contact_id: Optional[int] = None,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new reminder in Monica."""
            return await self.client.create_reminder(
                title=title, date=date, contact_id=contact_id, description=description
            )
        return create_reminder
    
    def _create_list_tasks_tool(self):
        @tool
        async def list_tasks(contact_id: Optional[int] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
            """List tasks from Monica."""
            return await self.client.list_tasks(contact_id=contact_id, limit=limit, page=page)
        return list_tasks
    
    def _create_create_task_tool(self):
        @tool
        async def create_task(
            title: str,
            contact_id: Optional[int] = None,
            description: Optional[str] = None,
            due_date: Optional[str] = None,
            is_completed: bool = False
        ) -> Dict[str, Any]:
            """Create a new task in Monica."""
            return await self.client.create_task(
                title=title, contact_id=contact_id, description=description,
                due_date=due_date, is_completed=is_completed
            )
        return create_task
    
    def _create_complete_task_tool(self):
        @tool
        async def complete_task(task_id: int) -> Dict[str, Any]:
            """Mark a task as completed."""
            return await self.client.complete_task(task_id=task_id)
        return complete_task
    
    def _create_list_gifts_tool(self):
        @tool
        async def list_gifts(contact_id: Optional[int] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
            """List gifts from Monica."""
            return await self.client.list_gifts(contact_id=contact_id, limit=limit, page=page)
        return list_gifts
    
    def _create_create_gift_tool(self):
        @tool
        async def create_gift(
            title: str,
            date: str,
            contact_id: Optional[int] = None,
            description: Optional[str] = None,
            budget: Optional[float] = None
        ) -> Dict[str, Any]:
            """Create a new gift in Monica."""
            return await self.client.create_gift(
                title=title, date=date, contact_id=contact_id,
                description=description, budget=budget
            )
        return create_gift
    
    def _create_list_debts_tool(self):
        @tool
        async def list_debts(contact_id: Optional[int] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
            """List debts from Monica."""
            return await self.client.list_debts(contact_id=contact_id, limit=limit, page=page)
        return list_debts
    
    def _create_create_debt_tool(self):
        @tool
        async def create_debt(
            reason: str,
            amount: float,
            date: str,
            contact_id: Optional[int] = None,
            description: Optional[str] = None,
            in_debt: bool = True
        ) -> Dict[str, Any]:
            """Create a new debt in Monica.
            
            Args:
                reason: The reason for the debt
                amount: The amount owed
                date: The date of the debt (YYYY-MM-DD)
                contact_id: Optional contact ID to associate with
                description: Optional description
                in_debt: Whether you are in debt (True) or the contact owes you (False)
            """
            return await self.client.create_debt(
                reason=reason, amount=amount, date=date, contact_id=contact_id,
                description=description, in_debt=in_debt
            )
        return create_debt
    
    def _create_list_journals_tool(self):
        @tool
        async def list_journals(contact_id: Optional[int] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
            """List journal entries from Monica."""
            return await self.client.list_journals(contact_id=contact_id, limit=limit, page=page)
        return list_journals
    
    def _create_create_journal_tool(self):
        @tool
        async def create_journal(
            title: str,
            date: str,
            content: str,
            contact_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """Create a new journal entry in Monica."""
            return await self.client.create_journal(
                title=title, date=date, content=content, contact_id=contact_id
            )
        return create_journal
    
    def _create_list_genders_tool(self):
        @tool
        async def list_genders() -> List[Dict[str, Any]]:
            """List available genders."""
            return await self.client.list_genders()
        return list_genders
    
    def _create_list_currencies_tool(self):
        @tool
        async def list_currencies() -> List[Dict[str, Any]]:
            """List available currencies."""
            return await self.client.list_currencies()
        return list_currencies
    
    async def list_tools(self) -> List[Any]:
        """Return the list of all available tools."""
        return self._tools
    
    async def close(self):
        """Close the underlying client."""
        await self.client.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
