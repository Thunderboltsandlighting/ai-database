"""
AI Optimization Configuration System

This module provides dynamic configuration optimization for Ada's AI model
based on conversation patterns, user preferences, and performance metrics.
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from utils.config import get_config
from utils.ada_memory import AdaMemory

@dataclass
class OptimizedConfig:
    """Optimized configuration parameters for Ada AI"""
    model_name: str = "llama3.1:8b"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2500
    conversation_memory: int = 6
    system_prompt_type: str = "conversational"
    creativity_boost: bool = False
    domain_specialization: str = "medical_billing"
    response_style: str = "detailed"
    anti_repetition_strength: float = 0.8

class AIOptimizationManager:
    """Manages AI model optimization based on user interactions and preferences"""
    
    def __init__(self):
        self.config = get_config()
        self.memory = AdaMemory()
        self.current_optimization = None
        self.optimization_history = []
    
    def get_optimized_ollama_config(self, question_context: str = "") -> Dict[str, Any]:
        """
        Get optimized Ollama configuration based on current conversation context
        and learned user preferences.
        
        Args:
            question_context: Current question or conversation context
            
        Returns:
            Optimized Ollama API configuration
        """
        # Analyze the question context
        question_type = self._classify_question_type(question_context)
        user_prefs = self._get_user_conversation_preferences()
        
        # Build optimized config
        base_config = {
            "model": self._select_optimal_model(question_type, user_prefs),
            "temperature": self._optimize_temperature(question_type, user_prefs),
            "top_p": self._optimize_top_p(question_type, user_prefs),
            "max_tokens": self._optimize_max_tokens(question_type, user_prefs),
            "stream": False,
            "options": {
                "seed": None,  # Allow randomness for variety
                "top_k": self._optimize_top_k(question_type, user_prefs),
                "repeat_penalty": self._optimize_repeat_penalty(user_prefs),
                "presence_penalty": 0.1,  # Encourage new topics
                "frequency_penalty": 0.2   # Reduce repetition
            }
        }
        
        # Add conversational enhancements based on user memory preferences
        if user_prefs.get('prefers_conversational', True):
            base_config["options"]["presence_penalty"] = 0.2
            base_config["options"]["frequency_penalty"] = 0.3
            base_config["temperature"] = min(0.85, base_config["temperature"] + 0.05)
        
        return base_config
    
    def get_enhanced_system_prompt(self, 
                                 question_context: str = "",
                                 conversation_history: List[Dict] = None) -> str:
        """
        Generate an enhanced system prompt optimized for the current context.
        
        Args:
            question_context: Current question or context
            conversation_history: Previous conversation messages
            
        Returns:
            Optimized system prompt
        """
        question_type = self._classify_question_type(question_context)
        user_prefs = self._get_user_conversation_preferences()
        
        # Base Ada personality
        base_prompt = """You are Ada, an expert medical billing AI assistant with deep healthcare industry knowledge and a genuine passion for helping practices succeed.

## YOUR CORE EXPERTISE:
- Medical billing and revenue cycle management
- Provider performance optimization and analytics
- Healthcare payer relationships and contract analysis
- Financial forecasting and business intelligence
- Practice management and operational efficiency

## YOUR PERSONALITY:
- Genuinely helpful and enthusiastic about their success
- Naturally conversational - never robotic or template-based
- Intellectually curious about their unique practice situation
- Proactive in identifying optimization opportunities
- Patient and thorough in explaining complex concepts"""

        # Add specialized knowledge based on question type
        if question_type == "provider_analysis":
            base_prompt += """

## PROVIDER ANALYSIS SPECIALIZATION:
- Deep understanding of provider compensation models
- Expertise in performance benchmarking and optimization
- Knowledge of provider comfort zones and burnout prevention
- Skills in growth planning and capacity analysis
- Experience with multi-provider practice dynamics"""

        elif question_type == "financial_analysis":
            base_prompt += """

## FINANCIAL ANALYSIS SPECIALIZATION:
- Advanced revenue cycle analytics and optimization
- Expertise in overhead analysis and cost management
- Knowledge of practice profitability modeling
- Skills in cash flow forecasting and planning
- Experience with financial performance benchmarking"""

        elif question_type == "strategic_planning":
            base_prompt += """

## STRATEGIC PLANNING SPECIALIZATION:
- Practice growth strategy and expansion planning
- Market analysis and competitive positioning
- Operational efficiency and workflow optimization
- Technology integration and automation opportunities
- Change management and implementation planning"""

        # Add conversational style optimization based on user preferences
        if user_prefs.get('prefers_detailed_analysis', True):
            base_prompt += """

## RESPONSE APPROACH:
- Provide comprehensive analysis with supporting data
- Include multiple perspectives and considerations
- Offer specific, actionable recommendations
- Connect insights to real business outcomes
- Suggest logical next steps and follow-up analysis"""
        else:
            base_prompt += """

## RESPONSE APPROACH:
- Focus on key insights and actionable takeaways
- Present information clearly and concisely
- Highlight the most important findings first
- Provide practical recommendations
- Ask clarifying questions when needed"""

        # Add anti-repetition instructions based on user memory preferences
        base_prompt += """

## CRITICAL COMMUNICATION GUIDELINES:
- NEVER use repetitive template responses
- Vary your language, tone, and approach in every response
- Build naturally on previous conversations
- Show genuine interest in their specific situation
- Ask thoughtful follow-up questions
- Reference their actual data and providers when relevant
- Avoid robotic or formulaic language patterns
- Make each response feel fresh and personalized"""

        # Add conversation context if available
        if conversation_history:
            recent_context = self._extract_conversation_context(conversation_history)
            if recent_context:
                base_prompt += f"""

## CURRENT CONVERSATION CONTEXT:
{recent_context}
                
Remember to build on this context naturally in your response."""

        return base_prompt
    
    def _classify_question_type(self, question: str) -> str:
        """Classify the type of question being asked"""
        question_lower = question.lower()
        
        # Provider-focused questions
        if any(term in question_lower for term in ['provider', 'dustin', 'tammy', 'isabel', 'sidney', 'doctor', 'practitioner']):
            return "provider_analysis"
        
        # Financial/business questions
        if any(term in question_lower for term in ['revenue', 'money', 'profit', 'cost', 'overhead', 'expense', 'financial', 'business']):
            return "financial_analysis"
        
        # Comparison questions
        if any(term in question_lower for term in ['compare', 'vs', 'versus', 'against', 'difference']):
            return "comparison_analysis"
        
        # Strategic questions
        if any(term in question_lower for term in ['strategy', 'growth', 'plan', 'future', 'goal', 'optimize', 'improve']):
            return "strategic_planning"
        
        # Technical/data questions
        if any(term in question_lower for term in ['data', 'report', 'analysis', 'trend', 'pattern', 'metric']):
            return "data_analysis"
        
        return "general_inquiry"
    
    def _get_user_conversation_preferences(self) -> Dict[str, Any]:
        """Get learned user conversation preferences"""
        # Analyze conversation patterns from memory
        recent_memories = self.memory.retrieve_memories(
            memory_type='conversation',
            limit=20,
            min_importance=5
        )
        
        preferences = {
            'prefers_conversational': True,  # Based on user memory preference
            'prefers_detailed_analysis': True,
            'response_length_preference': 'detailed',
            'technical_depth_preference': 'comprehensive',
            'follow_up_frequency': 'moderate'
        }
        
        if recent_memories:
            # Analyze patterns in recent conversations
            total_importance = sum(mem['importance'] for mem in recent_memories)
            avg_importance = total_importance / len(recent_memories)
            
            # High importance suggests user values detailed responses
            if avg_importance >= 8:
                preferences['prefers_detailed_analysis'] = True
                preferences['response_length_preference'] = 'comprehensive'
            elif avg_importance <= 5:
                preferences['response_length_preference'] = 'brief'
        
        return preferences
    
    def _select_optimal_model(self, question_type: str, user_prefs: Dict[str, Any]) -> str:
        """Select optimal model based on question type and preferences"""
        # For complex analysis, prefer larger model if available
        if question_type in ['financial_analysis', 'strategic_planning'] and user_prefs.get('prefers_detailed_analysis'):
            homelab_model = self.config.get('ollama.homelab_model')
            if homelab_model and self._test_model_availability(homelab_model):
                return homelab_model
        
        # Default to laptop model
        return self.config.get('ollama.laptop_model', 'llama3.1:8b')
    
    def _optimize_temperature(self, question_type: str, user_prefs: Dict[str, Any]) -> float:
        """Optimize temperature based on question type and user preferences"""
        base_temp = 0.7
        
        # Higher creativity for strategic and conversational questions
        if question_type in ['strategic_planning', 'general_inquiry']:
            base_temp = 0.8
        
        # Lower temperature for precise financial analysis
        elif question_type in ['financial_analysis', 'data_analysis']:
            base_temp = 0.6
        
        # Boost creativity if user prefers conversational responses
        if user_prefs.get('prefers_conversational', True):
            base_temp = min(0.85, base_temp + 0.05)
        
        return base_temp
    
    def _optimize_top_p(self, question_type: str, user_prefs: Dict[str, Any]) -> float:
        """Optimize top_p for response diversity"""
        if user_prefs.get('prefers_conversational', True):
            return 0.95  # Higher diversity for conversational responses
        
        if question_type in ['financial_analysis', 'data_analysis']:
            return 0.85  # More focused for analytical responses
        
        return 0.9
    
    def _optimize_max_tokens(self, question_type: str, user_prefs: Dict[str, Any]) -> int:
        """Optimize max tokens based on expected response length"""
        if user_prefs.get('response_length_preference') == 'comprehensive':
            return 4000
        elif user_prefs.get('response_length_preference') == 'brief':
            return 1500
        
        # Adjust based on question type
        if question_type in ['strategic_planning', 'financial_analysis']:
            return 3000
        elif question_type == 'general_inquiry':
            return 2000
        
        return 2500
    
    def _optimize_top_k(self, question_type: str, user_prefs: Dict[str, Any]) -> int:
        """Optimize top_k parameter"""
        if user_prefs.get('prefers_conversational', True):
            return 50  # Higher diversity
        
        if question_type in ['financial_analysis', 'data_analysis']:
            return 30  # More focused
        
        return 40
    
    def _optimize_repeat_penalty(self, user_prefs: Dict[str, Any]) -> float:
        """Optimize repeat penalty to avoid repetitive responses"""
        # Strong anti-repetition based on user memory preferences
        if user_prefs.get('prefers_conversational', True):
            return 1.2  # Strong penalty for repetition
        
        return 1.1
    
    def _test_model_availability(self, model_name: str) -> bool:
        """Test if a model is available"""
        try:
            import requests
            homelab_url = self.config.get('ollama.homelab_url')
            if homelab_url:
                response = requests.get(f"{homelab_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    return any(model['name'] == model_name for model in models)
        except Exception:
            pass
        
        return False
    
    def _extract_conversation_context(self, conversation_history: List[Dict]) -> str:
        """Extract relevant context from conversation history"""
        if not conversation_history:
            return ""
        
        # Get last 2-3 exchanges for context
        recent_messages = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
        
        context_parts = []
        for msg in recent_messages:
            role = "User" if msg.get('role') == 'user' else "Ada"
            content = msg.get('content', '')[:200]  # Limit length
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)

def get_optimization_manager() -> AIOptimizationManager:
    """Get singleton optimization manager instance"""
    if not hasattr(get_optimization_manager, '_instance'):
        get_optimization_manager._instance = AIOptimizationManager()
    return get_optimization_manager._instance 