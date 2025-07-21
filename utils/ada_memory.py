"""
Ada Memory System

This module provides memory management, personality customization, and 
custom instructions for the Ada AI assistant.
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class AdaMemory:
    """Memory management system for Ada AI assistant."""
    
    def __init__(self, db_path: str = "ada_memory.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the memory database with required tables."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            conn.executescript("""
                -- Memory storage for conversations and insights
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type VARCHAR(50) NOT NULL,  -- 'conversation', 'insight', 'preference', 'fact'
                    content TEXT NOT NULL,
                    context TEXT,  -- JSON context data
                    importance INTEGER DEFAULT 1,  -- 1-10 scale
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,  -- comma-separated tags
                    expires_at TIMESTAMP,  -- optional expiration
                    embedding_vector TEXT  -- for future semantic search
                );
                
                -- Personality configuration
                CREATE TABLE IF NOT EXISTS personality (
                    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR(50) NOT NULL,  -- 'communication', 'analysis', 'behavior'
                    setting_name VARCHAR(100) NOT NULL,
                    setting_value TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, setting_name)
                );
                
                -- Custom instructions from user
                CREATE TABLE IF NOT EXISTS custom_instructions (
                    instruction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR(50) NOT NULL,  -- 'general', 'analysis', 'reporting', 'communication'
                    instruction TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,  -- 1-10 priority
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- User preferences and context
                CREATE TABLE IF NOT EXISTS user_context (
                    context_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name VARCHAR(100),
                    role VARCHAR(100),  -- 'administrator', 'analyst', 'provider'
                    organization VARCHAR(200),
                    preferences TEXT,  -- JSON
                    timezone VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Session tracking
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_uuid VARCHAR(100) UNIQUE,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    conversation_summary TEXT,
                    key_insights TEXT,  -- JSON array
                    user_satisfaction INTEGER  -- 1-5 rating
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
                CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags);
            """)
            
            # Insert default personality settings
            self._insert_default_personality(conn)
            self._insert_default_instructions(conn)
            
            conn.commit()
            logger.info("Ada memory database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Ada memory database: {e}")
            raise
        finally:
            conn.close()
    
    def _insert_default_personality(self, conn):
        """Insert default personality settings."""
        default_personality = [
            ('communication', 'tone', 'friendly_professional', 'Friendly but professional communication style'),
            ('communication', 'detail_level', 'comprehensive', 'Provide comprehensive details with context'),
            ('communication', 'formality', 'casual_professional', 'Balance of casual and professional language'),
            ('analysis', 'depth', 'thorough', 'Provide thorough analysis with insights'),
            ('analysis', 'proactivity', 'high', 'Proactively suggest follow-up questions and next steps'),
            ('behavior', 'learning', 'adaptive', 'Learn from user interactions and preferences'),
            ('behavior', 'curiosity', 'high', 'Ask clarifying questions to better understand context'),
            ('reporting', 'visualization', 'enabled', 'Use charts and visual aids when appropriate'),
            ('reporting', 'actionability', 'high', 'Focus on actionable insights and recommendations')
        ]
        
        for category, name, value, description in default_personality:
            conn.execute("""
                INSERT OR IGNORE INTO personality (category, setting_name, setting_value, description)
                VALUES (?, ?, ?, ?)
            """, (category, name, value, description))
    
    def _insert_default_instructions(self, conn):
        """Insert default custom instructions."""
        # Insert sample instructions
        sample_instructions = [
            ('general', 'Always identify yourself as Ada, the database AI assistant', 8),
            ('communication', 'Use clear, professional language', 7),
            ('analysis', 'Provide actionable insights when possible', 6),
            ('general', 'Ask clarifying questions when ambiguous terms are used', 5),
            ('reporting', 'Format numerical data clearly with proper units', 4)
        ]
        
        for category, instruction, priority in sample_instructions:
            conn.execute("""
                INSERT OR IGNORE INTO custom_instructions (category, instruction, priority)
                VALUES (?, ?, ?)
            """, (category, instruction, priority))
    
    def store_memory(self, memory_type: str, content: str, context: Dict = None, 
                    importance: int = 5, tags: List[str] = None, expires_in_days: int = None) -> int:
        """Store a new memory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now() + timedelta(days=expires_in_days)
            
            context_json = json.dumps(context) if context else None
            tags_str = ','.join(tags) if tags else None
            
            cursor = conn.execute("""
                INSERT INTO memories (memory_type, content, context, importance, tags, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (memory_type, content, context_json, importance, tags_str, expires_at))
            
            memory_id = cursor.lastrowid
            conn.commit()
            logger.debug(f"Stored memory {memory_id}: {memory_type}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise
        finally:
            conn.close()
    
    def retrieve_memories(self, memory_type: str = None, tags: List[str] = None, 
                         limit: int = 10, min_importance: int = 1) -> List[Dict]:
        """Retrieve relevant memories."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            query = """
                SELECT * FROM memories 
                WHERE (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                AND importance >= ?
            """
            params = [min_importance]
            
            if memory_type:
                query += " AND memory_type = ?"
                params.append(memory_type)
            
            if tags:
                for tag in tags:
                    query += " AND tags LIKE ?"
                    params.append(f"%{tag}%")
            
            query += " ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            memories = []
            
            for row in cursor.fetchall():
                memory = dict(row)
                if memory['context']:
                    memory['context'] = json.loads(memory['context'])
                if memory['tags']:
                    memory['tags'] = memory['tags'].split(',')
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []
        finally:
            conn.close()
    
    def get_personality(self) -> Dict[str, Dict[str, str]]:
        """Get current personality settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("SELECT * FROM personality ORDER BY category, setting_name")
            personality = {}
            
            for row in cursor.fetchall():
                category = row['category']
                if category not in personality:
                    personality[category] = {}
                personality[category][row['setting_name']] = {
                    'value': row['setting_value'],
                    'description': row['description']
                }
            
            return personality
            
        except Exception as e:
            logger.error(f"Error retrieving personality: {e}")
            return {}
        finally:
            conn.close()
    
    def update_personality(self, category: str, setting_name: str, value: str) -> bool:
        """Update a personality setting."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute("""
                UPDATE personality 
                SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE category = ? AND setting_name = ?
            """, (value, category, setting_name))
            
            conn.commit()
            logger.info(f"Updated personality: {category}.{setting_name} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating personality: {e}")
            return False
        finally:
            conn.close()
    
    def get_custom_instructions(self, category: str = None, active_only: bool = True) -> List[Dict]:
        """Get custom instructions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            query = "SELECT * FROM custom_instructions"
            params = []
            
            conditions = []
            if active_only:
                conditions.append("active = 1")
            if category:
                conditions.append("category = ?")
                params.append(category)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY priority DESC, created_at ASC"
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error retrieving custom instructions: {e}")
            return []
        finally:
            conn.close()
    
    def add_custom_instruction(self, category: str, instruction: str, priority: int = 5) -> int:
        """Add a new custom instruction."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.execute("""
                INSERT INTO custom_instructions (category, instruction, priority)
                VALUES (?, ?, ?)
            """, (category, instruction, priority))
            
            instruction_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added custom instruction {instruction_id}: {instruction}")
            return instruction_id
            
        except Exception as e:
            logger.error(f"Error adding custom instruction: {e}")
            raise
        finally:
            conn.close()
    
    def get_user_context(self) -> Dict:
        """Get user context information."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("SELECT * FROM user_context ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            
            if row:
                context = dict(row)
                if context['preferences']:
                    context['preferences'] = json.loads(context['preferences'])
                return context
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error retrieving user context: {e}")
            return {}
        finally:
            conn.close()
    
    def update_user_context(self, **kwargs) -> bool:
        """Update user context information."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Check if context exists
            cursor = conn.execute("SELECT COUNT(*) FROM user_context")
            exists = cursor.fetchone()[0] > 0
            
            if 'preferences' in kwargs and isinstance(kwargs['preferences'], dict):
                kwargs['preferences'] = json.dumps(kwargs['preferences'])
            
            if exists:
                # Update existing
                set_clauses = []
                values = []
                for key, value in kwargs.items():
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
                
                values.append(datetime.now())
                set_clauses.append("updated_at = ?")
                
                query = f"UPDATE user_context SET {', '.join(set_clauses)}"
                conn.execute(query, values)
            else:
                # Insert new
                columns = list(kwargs.keys())
                placeholders = ['?'] * len(columns)
                query = f"INSERT INTO user_context ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                conn.execute(query, list(kwargs.values()))
            
            conn.commit()
            logger.info("Updated user context")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user context: {e}")
            return False
        finally:
            conn.close()
    
    def build_system_prompt(self, conversation_context: str = "") -> str:
        """Build a comprehensive system prompt with personality, instructions, and context."""
        personality = self.get_personality()
        instructions = self.get_custom_instructions()
        user_context = self.get_user_context()
        recent_memories = self.retrieve_memories(limit=5, min_importance=6)
        
        # Build system prompt
        prompt = "You are Ada, an intelligent database AI assistant. "
        
        # Add personality traits
        if personality:
            prompt += "\n\n## Your Personality:\n"
            for category, settings in personality.items():
                prompt += f"**{category.title()}:**\n"
                for setting, config in settings.items():
                    prompt += f"- {setting.replace('_', ' ').title()}: {config['value']} ({config['description']})\n"
        
        # Add custom instructions
        if instructions:
            prompt += "\n\n## Custom Instructions:\n"
            for instruction in instructions:
                prompt += f"- [{instruction['category'].title()}] {instruction['instruction']}\n"
        
        # Add user context
        if user_context:
            prompt += "\n\n## User Context:\n"
            if user_context.get('user_name'):
                prompt += f"- User Name: {user_context['user_name']}\n"
            if user_context.get('role'):
                prompt += f"- Role: {user_context['role']}\n"
            if user_context.get('organization'):
                prompt += f"- Organization: {user_context['organization']}\n"
        
        # Add relevant memories
        if recent_memories:
            prompt += "\n\n## Relevant Context from Previous Conversations:\n"
            for memory in recent_memories:
                prompt += f"- {memory['content']}\n"
        
        # Add conversation context
        if conversation_context:
            prompt += f"\n\n## Current Conversation Context:\n{conversation_context}\n"
        
        prompt += "\n\nRespond according to your personality and follow the custom instructions. Use the context to provide personalized, relevant assistance."
        
        return prompt
    
    def clean_expired_memories(self) -> int:
        """Clean up expired memories."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.execute("""
                DELETE FROM memories 
                WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP
            """)
            
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} expired memories")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning expired memories: {e}")
            return 0
        finally:
            conn.close()


class AdaPersonalityManager:
    """High-level personality management for Ada."""
    
    def __init__(self, memory: AdaMemory):
        self.memory = memory
    
    def set_communication_style(self, style: str):
        """Set Ada's communication style."""
        styles = {
            'professional': 'formal_professional',
            'friendly': 'friendly_professional', 
            'casual': 'casual_friendly',
            'technical': 'technical_detailed',
            'concise': 'brief_direct'
        }
        
        if style in styles:
            self.memory.update_personality('communication', 'tone', styles[style])
            return True
        return False
    
    def set_analysis_depth(self, depth: str):
        """Set Ada's analysis depth."""
        depths = {
            'basic': 'surface_level',
            'standard': 'comprehensive', 
            'detailed': 'thorough',
            'expert': 'deep_analytical'
        }
        
        if depth in depths:
            self.memory.update_personality('analysis', 'depth', depths[depth])
            return True
        return False
    
    def enable_proactive_suggestions(self, enabled: bool):
        """Enable/disable proactive suggestions."""
        value = 'high' if enabled else 'low'
        self.memory.update_personality('analysis', 'proactivity', value)
        return True 