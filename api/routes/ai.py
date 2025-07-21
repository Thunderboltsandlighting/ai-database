"""
AI API Routes.

This module provides AI endpoints for AI assistant interactions.
"""

import time
import sqlite3
import re
import random
import os
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest
from utils.config import get_config

from api.routes.ai_functions import get_provider_revenue, get_data_quality_issues, compare_payers, compare_providers, compare_providers_enhanced
from api.routes.ai_data_info import get_available_data_files, get_database_summary
from utils.ada_memory import AdaMemory
from api.routes.ai_business_reasoning import reasoning_engine

# Create Blueprint
ai_bp = Blueprint('ai', __name__)

# Initialize Ada memory system
ada_memory = None

def get_ada_memory():
    """Get or initialize Ada memory system."""
    global ada_memory
    if ada_memory is None:
        import os
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ada_memory.db')
        ada_memory = AdaMemory(db_path)
    return ada_memory

def get_db_connection():
    """Get database connection."""
    try:
        conn = sqlite3.connect(current_app.config.get('DATABASE_PATH', 'medical_billing.db'))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        current_app.logger.error(f"Error connecting to database: {e}")
        raise

@ai_bp.route('/status', methods=['GET'])
def ai_status():
    """Get AI assistant status."""
    # Check database connection
    db_status = "connected"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM providers")
        provider_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM payment_transactions")
        transaction_count = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
        provider_count = 0
        transaction_count = 0
    
    # Get CSV file information
    csv_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'csv_folder')
    uploads_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
    
    # Count CSV files in both folders
    csv_file_count = 0
    csv_categories = set()
    
    if os.path.exists(csv_folder):
        for dirpath, _, filenames in os.walk(csv_folder):
            category = os.path.basename(dirpath)
            csv_files = [f for f in filenames if f.lower().endswith('.csv')]
            csv_file_count += len(csv_files)
            if csv_files:
                csv_categories.add(category)
    
    if os.path.exists(uploads_folder):
        csv_files = [f for f in os.listdir(uploads_folder) if f.lower().endswith('.csv')]
        csv_file_count += len(csv_files)
        if csv_files:
            csv_categories.add('uploads')
    
    return jsonify({
        'status': 'ok',
        'ai_type': 'SimpleAI',
        'model': 'database-query',
        'database_path': current_app.config.get('DATABASE_PATH', 'medical_billing.db'),
        'database_status': db_status,
        'provider_count': provider_count,
        'transaction_count': transaction_count,
        'csv_file_count': csv_file_count,
        'csv_categories': list(csv_categories)
    })

@ai_bp.route('/chat', methods=['POST'])
def chat_with_ai():
    """Universal conversational AI that can answer any question about the dataset."""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            raise BadRequest("Missing 'message' parameter")
        
        message = data['message']
        history = data.get('history', [])
        
        print(f"DEBUG: Processing question: {message}")
        
        # Get Ada's memory system for context
        from utils.ada_memory import AdaMemory
        memory = AdaMemory()
        
        # Build conversation context from history
        conversation_context = ""
        if history:
            recent_messages = history[-6:]  # Last 3 exchanges
            for msg in recent_messages:
                role = "User" if msg.get("role") == "user" else "Ada"
                conversation_context += f"{role}: {msg.get('content', '')}\n"
        
        # Extract provider names for specialized routing
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            provider_names = extract_provider_names_universal(message, cursor)
            conn.close()
        except Exception as e:
            current_app.logger.error(f"Error extracting provider names: {e}")
            provider_names = []
        
        # Check for specific function calls first
        if "compare" in message.lower() and len(provider_names) == 2:
            try:
                current_app.logger.info(f"Routing to provider comparison: {provider_names}")
                from api.routes.ai_functions import compare_providers_enhanced
                comparison_result = compare_providers_enhanced(provider_names[0], provider_names[1])
                return jsonify({"response": comparison_result})
            except Exception as e:
                current_app.logger.error(f"Error in provider comparison: {e}")
                return jsonify({"response": f"I encountered an error performing the comparison: {str(e)}"})
        
        # Check for provider overhead coverage analysis (ANY provider)
        provider_overhead_terms = any(term in message.lower() for term in ["overhead", "expenses", "cover", "pulling", "weight", "monthly costs", "break even", "profitability"])
        
        if provider_names and provider_overhead_terms:
            try:
                # Use the first provider mentioned for analysis
                target_provider = provider_names[0]
                current_app.logger.info(f"Routing to {target_provider} overhead coverage analysis")
                
                # Get the provider's overhead analysis data
                import requests
                analysis_url = f"http://localhost:5001/api/analytics/provider-overhead-analysis/{target_provider}"
                response = requests.get(analysis_url)
                
                if response.status_code == 200:
                    analysis_data = response.json()
                    if analysis_data.get('success'):
                        overhead_result = analysis_data['analysis_text']
                        
                        # Build enhanced prompt with actual data
                        enhanced_prompt = f"""
User Question: {message}

ACTUAL DATA ANALYSIS for {target_provider}:
{overhead_result}

Please analyze this data and provide a conversational, business-focused response about whether {target_provider} is covering the overhead expenses. Use ONLY the numbers provided above. Do not make up any figures.
"""
                        
                        response = call_ollama_with_enhanced_context(enhanced_prompt, conversation_context, memory)
                        return jsonify({"response": response})
                    else:
                        return jsonify({"response": f"I encountered an error analyzing {target_provider}'s overhead coverage: {analysis_data.get('error', 'Unknown error')}"})
                else:
                    return jsonify({"response": f"I couldn't retrieve the overhead analysis for {target_provider}. The analysis service may be unavailable."})
                
            except Exception as e:
                current_app.logger.error(f"Error in {target_provider} overhead analysis: {e}")
                return jsonify({"response": f"I encountered an error analyzing {target_provider}'s overhead coverage: {str(e)}"})
        
        # Universal conversational AI for all other questions
        data_context = build_universal_data_context(message)
        
        # Create intelligent conversational prompt
        user_prompt = f"""The user asked: "{message}"

Here's relevant data from their medical billing database:
{data_context}

Respond as Ada, their intelligent medical billing assistant. Be conversational, insightful, and helpful.

Guidelines:
- Answer their question directly using the data provided
- Explain what the numbers mean for their business
- Provide actionable insights and recommendations
- Be natural and engaging, not robotic
- If you need more specific data, suggest what they should ask
- Always offer relevant follow-up analysis

Current conversation context:
{conversation_context}

Response:"""

        # Get conversational response with enhanced context
        response = call_ollama_with_enhanced_context(user_prompt, conversation_context, memory)
        
        # Store this interaction in Ada's memory
        if response and len(response) > 20:
            memory.store_memory(
                memory_type='conversation',
                content=f"User: {message} | Ada: {response[:200]}...",
                context={'user_question': message, 'response_type': 'universal_conversational'},
                importance=7,
                tags=['conversation', 'universal_ai']
            )
        
        # Create updated history
        updated_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response}
        ]
        
        return jsonify({
            'message': message,
            'response': response,
            'history': updated_history,
            'elapsed_time': 0.5,
            'ai_mode': 'universal_conversational'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in universal AI chat: {e}")
        return jsonify({
            'message': message if 'message' in locals() else "unknown",
            'response': f"I apologize, but I encountered an error while analyzing your data. Please try rephrasing your question or ask about something specific like provider performance or revenue trends.",
            'error': str(e),
            'history': history if 'history' in locals() else []
        }), 400

@ai_bp.route('/data-info', methods=['GET'])
def get_data_info():
    """Get information about available data files and database content."""
    try:
        files_info = get_available_data_files()
        db_info = get_database_summary()
        
        return jsonify({
            'files_info': files_info,
            'database_info': db_info
        })
    except Exception as e:
        current_app.logger.error(f"Error getting data info: {e}")
        return jsonify({
            'error': str(e)
        }), 500


# Initialize global config
config = get_config()

def call_ollama(prompt, system_message=None):
    """Call Ollama API directly for truly conversational responses"""
    # Get Ollama config
    ollama_url = config.get("ollama.laptop_url", "http://localhost:11434")
    model = config.get("ollama.laptop_model", "llama3.1:8b")
    temperature = config.get("ollama.temperature", 0.7)
    timeout = config.get("ollama.timeout", 60)
    
    # Create messages array
    messages = []
    
    # Add system message if provided
    if system_message:
        messages.append({"role": "system", "content": system_message})
    else:
        # Default system message
        messages.append({
            "role": "system", 
            "content": "You are Ada, a helpful and conversational database AI assistant. "
                       "Respond in a natural, friendly tone. Offer meaningful insights about the data "
                       "and suggest next steps when appropriate. Be concise but thorough, and don't "
                       "be afraid to ask clarifying questions when needed."
        })
    
    # Add the user prompt
    messages.append({"role": "user", "content": prompt})
    
    try:
        # Make the request to Ollama
        response = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            },
            timeout=timeout
        )
        
        # Check if request was successful
        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            current_app.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        current_app.logger.error(f"Error calling Ollama: {e}")
        return None

def make_conversational(response, question, history):
    """Make the AI response more conversational using Ada's memory and personality system."""
    try:
        # Get Ada's memory system
        memory = get_ada_memory()
        
        # Store key insights from the interaction as memory
        if response and len(response) > 50:  # Only store substantial responses
            memory.store_memory(
                memory_type='insight',
                content=f"User asked: '{question}' - Key data: {response[:200]}...",
                context={'question': question, 'response_type': 'data_query'},
                importance=5,
                tags=['conversation', 'data_query']
            )
        
        # Extract context from conversation history
        context = ""
        if history:
            recent_messages = history[-4:]  # Last 2 exchanges
            for msg in recent_messages:
                role = "User" if msg.get("role") == "user" else "Ada"
                context += f"{role}: {msg.get('content', '')}\n"
        
        # Build system prompt with Ada's personality and memory
        system_prompt = memory.build_system_prompt(context)
        
        # Create the user prompt
        user_prompt = f"""The user asked: "{question}"

Here's the data from the database:
{response}

Transform this data into a natural, conversational response that:
1. Acknowledges their question personally
2. Presents the key insights from the data in an engaging way  
3. Provides context about what the numbers mean
4. Suggests 1-2 relevant follow-up questions or next steps
5. Maintains continuity with previous conversation

Response:"""
        
        # Try to get a response from Ollama with enhanced system prompt
        ollama_response = call_ollama(user_prompt, system_prompt)
        
        # If Ollama response is successful, return it
        if ollama_response:
            return ollama_response
            
    except Exception as e:
        current_app.logger.error(f"Error in enhanced conversational mode: {e}")
        # Fall back to basic mode on error
    
    # Try to get a response from Ollama
    ollama_response = call_ollama(user_prompt)
    
    # If Ollama response is successful, return it
    if ollama_response:
        return ollama_response
    
    # If Ollama fails, fall back to the template-based approach
    is_first_message = len(history) <= 2  # Only user's first message and possibly the welcome
    user_name = extract_user_name(history)
    
    # Add follow-up questions based on the response content
    if "provider" in response.lower() and "revenue" in response.lower():
        follow_ups = [
            "Would you like to see how this compares to previous months?",
            "Would you like to see a breakdown by payer for this provider?",
            "Is there another provider you'd like to analyze?"
        ]
        response = f"{response}\n\n{random.choice(follow_ups)}"
    
    elif "data files" in response.lower() or "csv files" in response.lower():
        follow_ups = [
            "Would you like me to help you analyze any specific data from these files?",
            "What specific insights are you looking for from your billing data?",
            "Would you like to see revenue trends or provider performance from this data?"
        ]
        response = f"{response}\n\n{random.choice(follow_ups)}"
    
    elif "data quality" in response.lower() or "issues" in response.lower():
        follow_ups = [
            "Would you like suggestions on how to fix these issues?",
            "Would you like to see which providers are most affected by these issues?",
            "Would you like to generate a detailed report on these issues?"
        ]
        response = f"{response}\n\n{random.choice(follow_ups)}"
    
    elif "payer" in response.lower() or "compare" in response.lower():
        follow_ups = [
            "Would you like to see which provider performs best with these payers?",
            "Would you like to see trends over time for these payers?",
            "Is there another payer comparison you'd like to see?"
        ]
        response = f"{response}\n\n{random.choice(follow_ups)}"
    
    # Add personalization if we have the user's name
    if user_name and random.random() < 0.3:  # 30% chance to use name
        response = f"{user_name}, {response.lower()[0]}{response[1:]}"
    
    # For first-time users, add more guidance
    if is_first_message and not any(x in response.lower() for x in ["follow_ups", "would you like"]):
        tips = [
            "\n\nYou can ask me about specific providers, revenue analysis, payer comparisons, or data quality issues. What would you like to explore?",
            "\n\nIs there a specific aspect of your billing data you'd like to analyze?",
            "\n\nWould you like me to suggest some analyses based on your data?"
        ]
        response += random.choice(tips)
    
    return response

def extract_provider_names(message):
    """Extract provider names from message"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT provider_name FROM providers")
        all_providers = cursor.fetchall()
        conn.close()
        
        all_providers = sorted([p['provider_name'] for p in all_providers], key=len, reverse=True)
        provider_names = []
        
        message_lower = message.lower()
        
        # First pass: exact matches
        for provider in all_providers:
            if provider.lower() in message_lower:
                provider_names.append(provider)
        
        # Second pass: partial matches
        if len(provider_names) < 2:
            for provider in all_providers:
                if provider not in provider_names:
                    name_parts = provider.lower().split()
                    for part in name_parts:
                        if len(part) > 2 and part in message_lower:
                            provider_names.append(provider)
                            break
                if len(provider_names) >= 2:
                    break
        
        return provider_names[:2]  # Return max 2 providers
    except Exception as e:
        current_app.logger.error(f"Error extracting provider names: {e}")
        return []

def extract_user_name(history):
    """Try to extract user's name from conversation history."""
    # Look for introduction patterns in previous messages
    for message in history:
        if message.get('role') == 'user':
            content = message.get('content', '').lower()
            # Look for "my name is" or "I'm" patterns
            name_match = re.search(r"my name is (\w+)", content) or re.search(r"i am (\w+)", content) or re.search(r"i'm (\w+)", content)
            if name_match:
                return name_match.group(1).capitalize()
    return None

def get_capabilities_message():
    """Return a message about what the AI assistant can do."""
    return (
        "I'm your data analyst. Here's what I can help you with:\n\n"
        "📊 **Data Analysis**\n"
        "- Revenue analysis by provider, payer, or time period\n"
        "- Provider performance comparisons\n"
        "- Payer comparison (rates, denials, etc.)\n"
        "- Data quality assessment\n\n"
        "📁 **Data Management**\n"
        "- Information about available data files\n"
        "- Database content summary\n"
        "- Guidance on importing and managing your data\n\n"
        "💡 **Insights & Recommendations**\n"
        "- Identifying top performers\n"
        "- Highlighting revenue opportunities\n"
        "- Flagging potential data issues\n\n"
        "What would you like to explore today?"
    )

def get_top_provider():
    """Get the top performing provider based on revenue."""
    try:
        conn = get_db_connection()
        query = """
        SELECT p.provider_name, SUM(pt.cash_applied) as total_revenue, COUNT(*) as transaction_count
        FROM providers p
        JOIN payment_transactions pt ON p.provider_id = pt.provider_id
        GROUP BY p.provider_id
        ORDER BY total_revenue DESC
        LIMIT 1
        """
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        conn.close()
        
        if result and result['total_revenue']:
            return f"The top performing provider is {result['provider_name']} with a total revenue of ${float(result['total_revenue']):,.2f} from {result['transaction_count']} transactions."
        else:
            return "I couldn't find any provider revenue data in the database. Please check that you have payment transactions with valid provider IDs."
    except Exception as e:
        current_app.logger.error(f"Error getting top provider: {e}")
        return "I encountered an error while trying to retrieve provider data. Please check the database connection and schema."

def get_all_providers():
    """Get all providers from the database.
    
    Returns:
        str: Formatted list of all providers with their specialties
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT provider_name, specialty, 
                   COUNT(pt.transaction_id) as transaction_count,
                   SUM(pt.cash_applied) as total_revenue
            FROM providers p
            LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
            WHERE p.active = 1 
                AND p.provider_name NOT IN ('Test Provider', 'Another Provider', 'Unknown')
                AND p.provider_name IS NOT NULL
                AND p.provider_name != ''
            GROUP BY p.provider_id, p.provider_name, p.specialty
            ORDER BY total_revenue DESC NULLS LAST, p.provider_name
        """)
        providers = cursor.fetchall()
        conn.close()
        
        if not providers:
            return "I don't see any providers in the database yet. You may need to upload some CSV files with provider data first."
        
        # Format the response
        response = f"Here are your {len(providers)} active providers:\n\n"
        
        for provider in providers:
            name = provider['provider_name']
            specialty = provider['specialty'] or "Mental Health Services"
            transaction_count = provider['transaction_count'] or 0
            total_revenue = provider['total_revenue'] or 0
            
            response += f"• **{name}**"
            if specialty != "Mental Health Services":
                response += f" ({specialty})"
            if transaction_count > 0:
                response += f" - {transaction_count:,} transactions, ${total_revenue:,.2f} revenue"
            response += "\n"
        
        response += f"\nWould you like more details about any specific provider or their performance?"
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error getting all providers: {e}")
        return "I encountered an error while retrieving the provider list. Please check the database connection."

def get_provider_details(provider_name):
    """Get detailed information about a specific provider.
    
    Args:
        provider_name (str): Name of the provider to look up
        
    Returns:
        str: Formatted provider details including revenue, transactions, and recent activity
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get provider basic info and stats
        cursor.execute("""
            SELECT 
                p.provider_name,
                p.specialty,
                p.npi_number,
                COUNT(pt.transaction_id) as total_transactions,
                SUM(pt.cash_applied) as total_revenue,
                AVG(pt.cash_applied) as avg_payment,
                MIN(pt.transaction_date) as first_transaction,
                MAX(pt.transaction_date) as last_transaction,
                COUNT(DISTINCT pt.payer_name) as unique_payers
            FROM providers p
            LEFT JOIN payment_transactions pt ON p.provider_id = pt.provider_id
            WHERE p.provider_name LIKE ?
            GROUP BY p.provider_id, p.provider_name, p.specialty, p.npi_number
        """, (f"%{provider_name}%",))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return f"I couldn't find a provider named '{provider_name}' in the database. Here are the available providers: {', '.join([p['provider_name'] for p in get_all_providers_list()])}"
        
        # Get monthly breakdown for the last 6 months
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', pt.transaction_date) as month,
                COUNT(*) as transactions,
                SUM(pt.cash_applied) as revenue
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            WHERE p.provider_name LIKE ?
                AND pt.transaction_date >= date('now', '-6 months')
            GROUP BY strftime('%Y-%m', pt.transaction_date)
            ORDER BY month DESC
            LIMIT 6
        """, (f"%{provider_name}%",))
        
        monthly_data = cursor.fetchall()
        
        # Get top payers for this provider
        cursor.execute("""
            SELECT 
                pt.payer_name,
                COUNT(*) as transactions,
                SUM(pt.cash_applied) as revenue
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            WHERE p.provider_name LIKE ?
                AND pt.payer_name IS NOT NULL
                AND pt.payer_name != ''
            GROUP BY pt.payer_name
            ORDER BY revenue DESC
            LIMIT 5
        """, (f"%{provider_name}%",))
        
        top_payers = cursor.fetchall()
        conn.close()
        
        # Format response
        response = f"**{result['provider_name']}**\n\n"
        
        if result['specialty']:
            response += f"**Specialty:** {result['specialty']}\n"
        if result['npi_number']:
            response += f"**NPI:** {result['npi_number']}\n"
        
        response += f"\n**Performance Summary:**\n"
        response += f"• Total Transactions: {result['total_transactions']:,}\n"
        response += f"• Total Revenue: ${result['total_revenue']:,.2f}\n"
        response += f"• Average Payment: ${result['avg_payment']:,.2f}\n"
        response += f"• Unique Payers: {result['unique_payers']}\n"
        
        if result['first_transaction'] and result['last_transaction']:
            response += f"• Active Period: {result['first_transaction']} to {result['last_transaction']}\n"
        
        # Add monthly breakdown
        if monthly_data:
            response += f"\n**Recent Monthly Activity:**\n"
            for month_data in monthly_data:
                response += f"• {month_data['month']}: {month_data['transactions']} transactions, ${month_data['revenue']:,.2f}\n"
        
        # Add top payers
        if top_payers:
            response += f"\n**Top Payers:**\n"
            for payer in top_payers:
                response += f"• {payer['payer_name']}: ${payer['revenue']:,.2f} ({payer['transactions']} transactions)\n"
        
        response += f"\nWould you like more specific analysis or comparisons for {result['provider_name']}?"
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error getting provider details for {provider_name}: {e}")
        return f"I encountered an error while retrieving details for {provider_name}. Please check the database connection."

def get_all_providers_list():
    """Helper function to get just provider names for error messages."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT provider_name FROM providers WHERE active = 1 ORDER BY provider_name")
        providers = [row['provider_name'] for row in cursor.fetchall()]
        conn.close()
        return providers
    except:
        return []

def format_business_analysis(analysis_result):
    """Formats the structured reasoning result into a natural language response."""
    if not analysis_result or 'error' in analysis_result:
        return "I couldn't analyze the business question based on the provided data."

    response = f"🧠 **Business Analysis for:** {analysis_result.get('question', 'Unknown question')}\n\n"
    
    # Show question classification
    if analysis_result.get('question_type'):
        response += f"**Analysis Type:** {analysis_result['question_type'].title()}\n\n"
    
    # Show reasoning steps
    if analysis_result.get('reasoning_steps'):
        response += "**Analysis Steps:**\n"
        for step in analysis_result['reasoning_steps']:
            if step.get('result') and not isinstance(step['result'], dict):
                response += f"{step['step_number']}. {step['description']}\n"
                # Show data results if available
                if isinstance(step['result'], list) and step['result']:
                    for record in step['result'][:3]:  # Show first 3 records
                        if isinstance(record, dict):
                            for key, value in record.items():
                                if isinstance(value, (int, float)):
                                    if 'revenue' in key.lower() or 'cash' in key.lower():
                                        response += f"   • {key}: ${value:,.2f}\n"
                                    else:
                                        response += f"   • {key}: {value:,}\n"
                                else:
                                    response += f"   • {key}: {value}\n"
                            response += "\n"
        response += "\n"
    
    # Show conclusion
    if analysis_result.get('conclusion'):
        response += f"**Conclusion:** {analysis_result['conclusion']}\n\n"
    
    # Show recommendations
    if analysis_result.get('recommendations'):
        response += "**Recommendations:**\n"
        for rec in analysis_result['recommendations']:
            response += f"• {rec}\n"
        response += "\n"
    
    response += "Would you like me to dive deeper into any specific aspect or run additional analysis?"
    return response

def call_ollama_with_context(user_prompt, conversation_context, memory):
    """Enhanced Ollama call with conversation context and memory"""
    try:
        # Build comprehensive system prompt
        system_prompt = memory.build_system_prompt(conversation_context)
        
        # Add specific instructions for medical billing context
        enhanced_system = f"""{system_prompt}

## Medical Billing Context:
You are analyzing medical billing data for a healthcare practice. Be knowledgeable about:
- Provider performance and compensation
- Revenue trends and patterns  
- Payer relationships and patterns
- Business optimization strategies
- Healthcare industry terminology

## Response Guidelines:
- Be conversational and engaging, not robotic
- Provide actionable insights, not just data
- Use natural language, avoid repetitive phrases
- Ask relevant follow-up questions
- Explain what the numbers mean for their business
- Vary your language and tone to avoid repetition"""

        response = call_ollama(user_prompt, enhanced_system)
        
        if response:
            return response
        else:
            return "I'm having trouble processing that right now. Could you rephrase your question or try asking about something specific like provider performance or revenue trends?"
            
    except Exception as e:
        current_app.logger.error(f"Error in enhanced Ollama call: {e}")
        return "I apologize, but I'm experiencing some technical difficulties. Please try your question again."

def build_universal_data_context(message):
    """Build relevant data context for any question about the dataset."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        message_lower = message.lower()
        data_context = ""
        
        # Extract any provider names mentioned
        provider_names = extract_provider_names_universal(message, cursor)
        
        # Check for specific function calls first
        if "compare" in message_lower and len(provider_names) == 2:
            try:
                current_app.logger.info(f"Routing to provider comparison: {provider_names}")
                comparison_result = compare_providers_enhanced(provider_names[0], provider_names[1])
                return jsonify({"response": comparison_result})
            except Exception as e:
                current_app.logger.error(f"Error in provider comparison: {e}")
                return jsonify({"response": f"I encountered an error performing the comparison: {str(e)}"})
        
        # Check for provider overhead coverage analysis (ANY provider)
        elif any(term in message_lower for term in ["overhead", "expenses", "cover", "pulling", "weight", "monthly costs", "break even", "profitability"]) and provider_names:
            try:
                # Use the first provider mentioned for analysis
                target_provider = provider_names[0]
                current_app.logger.info(f"Routing to {target_provider} overhead coverage analysis")
                
                # Get the provider's overhead analysis data
                import requests
                analysis_url = f"http://localhost:5001/api/analytics/provider-overhead-analysis/{target_provider}"
                response = requests.get(analysis_url)
                
                if response.status_code == 200:
                    analysis_data = response.json()
                    if analysis_data.get('success'):
                        overhead_result = analysis_data['analysis_text']
                        
                        # Build enhanced prompt with actual data
                        enhanced_prompt = f"""
User Question: {message}

ACTUAL DATA ANALYSIS for {target_provider}:
{overhead_result}

Please analyze this data and provide a conversational, business-focused response about whether {target_provider} is covering the overhead expenses. Use ONLY the numbers provided above. Do not make up any figures.
"""
                        
                        response = call_ollama_with_enhanced_context(enhanced_prompt, conversation_context, memory)
                        return jsonify({"response": response})
                    else:
                        return jsonify({"response": f"I encountered an error analyzing {target_provider}'s overhead coverage: {analysis_data.get('error', 'Unknown error')}"})
                else:
                    return jsonify({"response": f"I couldn't retrieve the overhead analysis for {target_provider}. The analysis service may be unavailable."})
                
            except Exception as e:
                current_app.logger.error(f"Error in {target_provider} overhead analysis: {e}")
                return jsonify({"response": f"I encountered an error analyzing {target_provider}'s overhead coverage: {str(e)}"})
        
        # Universal conversational AI for all other questions
        # Get provider-specific data if providers mentioned
        if provider_names:
            if len(provider_names) == 2:
                # Provider comparison
                try:
                    comparison_data = compare_providers_enhanced(provider_names[0], provider_names[1])
                    data_context += f"\n=== PROVIDER COMPARISON: {provider_names[0]} vs {provider_names[1]} ===\n"
                    data_context += comparison_data
                except Exception as e:
                    data_context += f"\n=== PROVIDER DATA ===\n"
                    for provider in provider_names:
                        provider_data = get_provider_summary(provider, cursor)
                        data_context += f"\n{provider}: {provider_data}\n"
            else:
                # Single provider analysis
                for provider in provider_names:
                    provider_data = get_provider_summary(provider, cursor)
                    data_context += f"\n=== {provider} PERFORMANCE ===\n{provider_data}\n"
        
        # Add expense context for expense-related questions
        if any(term in message_lower for term in ["expense", "cost", "overhead", "spending", "budget", "cvlc_expenses", "hvlc_expenses", "monthly costs", "fixed costs", "variable costs"]):
            expense_data = get_expense_summary(cursor)
            data_context += f"\n=== EXPENSE ANALYSIS ===\n{expense_data}\n"
        
        # Add business context for business-related questions
        if any(term in message_lower for term in ["business", "revenue", "profit", "growth", "performance", "money", "financial", "trends"]):
            business_data = get_business_summary(cursor)
            data_context += f"\n=== BUSINESS OVERVIEW ===\n{business_data}\n"
        
        # Add payer context for payer-related questions
        if any(term in message_lower for term in ["payer", "insurance", "bcbs", "aetna", "payment", "claims"]):
            payer_data = get_payer_summary(cursor)
            data_context += f"\n=== PAYER ANALYSIS ===\n{payer_data}\n"
        
        # Add date-specific context if dates mentioned
        date_context = extract_date_context(message)
        if date_context:
            period_data = get_period_summary(date_context, cursor)
            data_context += f"\n=== PERIOD ANALYSIS ({date_context}) ===\n{period_data}\n"
        
        # Add general context if no specific focus detected
        if not data_context:
            general_data = get_general_summary(cursor)
            data_context += f"\n=== GENERAL DATA OVERVIEW ===\n{general_data}\n"
        
        conn.close()
        return data_context
        
    except Exception as e:
        current_app.logger.error(f"Error building data context: {e}")
        return "I encountered an issue accessing your data. Please try your question again."

def extract_provider_names_universal(message, cursor):
    """Extract provider names from message using universal provider detection"""
    try:
        cursor.execute("SELECT provider_name FROM providers WHERE active = 1")
        all_providers = cursor.fetchall()
        
        all_providers = sorted([p[0] for p in all_providers], key=len, reverse=True)
        provider_names = []
        
        message_lower = message.lower()
        
        # Check for exact matches first
        for provider in all_providers:
            if provider.lower() in message_lower:
                provider_names.append(provider)
        
        # Check for partial matches (first names)
        if len(provider_names) < 2:
            for provider in all_providers:
                if provider not in provider_names:
                    name_parts = provider.lower().split()
                    for part in name_parts:
                        if len(part) > 2 and part in message_lower:
                            provider_names.append(provider)
                            break
                if len(provider_names) >= 2:
                    break
        
        return provider_names[:2]  # Return max 2 providers
    except Exception as e:
        current_app.logger.error(f"Error extracting provider names: {e}")
        return []

def get_provider_summary(provider_name, cursor):
    """Get comprehensive provider summary."""
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as transactions,
                SUM(cash_applied) as total_revenue,
                AVG(cash_applied) as avg_payment,
                MIN(transaction_date) as first_date,
                MAX(transaction_date) as last_date,
                COUNT(DISTINCT payer_name) as unique_payers
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            WHERE p.provider_name = ?
        """, (provider_name,))
        
        summary = cursor.fetchone()
        if summary:
            return f"{summary[0]} transactions, ${summary[1]:,.2f} revenue, ${summary[2]:.2f} avg payment, {summary[5]} payers, active {summary[3]} to {summary[4]}"
        return "No data found"
    except Exception as e:
        return f"Error retrieving data: {e}"

def get_business_summary(cursor):
    """Get high-level business summary."""
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(cash_applied) as total_revenue,
                COUNT(DISTINCT p.provider_name) as active_providers,
                MIN(transaction_date) as first_date,
                MAX(transaction_date) as last_date
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            WHERE pt.transaction_date >= date('now', '-12 months')
        """)
        
        summary = cursor.fetchone()
        if summary:
            return f"Last 12 months: {summary[0]:,} transactions, ${summary[1]:,.2f} revenue, {summary[2]} active providers, period {summary[3]} to {summary[4]}"
        return "No recent business data found"
    except Exception as e:
        return f"Error retrieving business data: {e}"

def get_payer_summary(cursor):
    """Get payer analysis summary."""
    try:
        cursor.execute("""
            SELECT 
                payer_name,
                COUNT(*) as transactions,
                SUM(cash_applied) as revenue
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            WHERE pt.transaction_date >= date('now', '-6 months')
            GROUP BY payer_name
            ORDER BY revenue DESC
            LIMIT 5
        """)
        
        payers = cursor.fetchall()
        if payers:
            result = "Top payers (last 6 months):\n"
            for payer in payers:
                result += f"- {payer[0]}: {payer[1]} transactions, ${payer[2]:,.2f}\n"
            return result
        return "No payer data found"
    except Exception as e:
        return f"Error retrieving payer data: {e}"

def extract_date_context(message):
    """Extract date context from message."""
    import re
    message_lower = message.lower()
    
    # Check for specific months/years
    months = ['january', 'february', 'march', 'april', 'may', 'june', 
             'july', 'august', 'september', 'october', 'november', 'december']
    
    for month in months:
        if month in message_lower:
            year_match = re.search(r'\b(\d{4})\b', message_lower)
            if year_match:
                return f"{month} {year_match.group(1)}"
    
    # Check for year only
    year_match = re.search(r'\b(20\d{2})\b', message_lower)
    if year_match:
        return year_match.group(1)
    
    # Check for relative dates
    if "last month" in message_lower:
        return "last month"
    elif "this month" in message_lower:
        return "this month"
    elif "last year" in message_lower:
        return "last year"
    
    return None

def get_period_summary(period, cursor):
    """Get summary for specific time period."""
    try:
        # This is a simplified version - you can enhance based on the period format
        cursor.execute("""
            SELECT 
                COUNT(*) as transactions,
                SUM(cash_applied) as revenue,
                COUNT(DISTINCT p.provider_name) as providers
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
            WHERE pt.transaction_date >= date('now', '-3 months')
        """)
        
        summary = cursor.fetchone()
        if summary:
            return f"Recent period: {summary[0]} transactions, ${summary[1]:,.2f} revenue, {summary[2]} providers active"
        return "No data for specified period"
    except Exception as e:
        return f"Error retrieving period data: {e}"

def get_general_summary(cursor):
    """Get general data overview."""
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(cash_applied) as total_revenue,
                COUNT(DISTINCT p.provider_name) as total_providers,
                COUNT(DISTINCT payer_name) as total_payers
            FROM payment_transactions pt
            JOIN providers p ON pt.provider_id = p.provider_id
        """)
        
        summary = cursor.fetchone()
        if summary:
            return f"Database overview: {summary[0]:,} total transactions, ${summary[1]:,.2f} total revenue, {summary[2]} providers, {summary[3]} payers"
        return "No data available"
    except Exception as e:
        return f"Error retrieving general data: {e}"

def get_expense_summary(cursor):
    """Get comprehensive expense analysis."""
    try:
        # Check if expense data exists
        cursor.execute("SELECT COUNT(*) FROM expense_transactions")
        expense_count = cursor.fetchone()[0]
        
        if expense_count == 0:
            return "No expense data found in the database."
        
        # Get detailed expense breakdown
        cursor.execute("""
            SELECT 
                category,
                subcategory,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                COUNT(*) as frequency,
                status,
                frequency as payment_frequency
            FROM expense_transactions
            WHERE status = 'active'
            GROUP BY category, subcategory, status, frequency
            ORDER BY total_amount DESC
        """)
        
        expenses = cursor.fetchall()
        
        if not expenses:
            return "No active expenses found."
        
        # Get monthly total
        cursor.execute("""
            SELECT SUM(amount) as monthly_total
            FROM expense_transactions
            WHERE status = 'active' AND frequency = 'monthly'
        """)
        
        monthly_total = cursor.fetchone()[0] or 0
        
        # Build expense summary
        result = f"Monthly expense total: ${monthly_total:,.2f}\n\n"
        result += "Expense breakdown by category:\n"
        
        current_category = None
        category_total = 0
        
        for expense in expenses:
            if current_category != expense[0]:
                if current_category:
                    result += f"  → Category total: ${category_total:,.2f}\n\n"
                current_category = expense[0]
                category_total = 0
                result += f"{current_category.upper()}:\n"
            
            category_total += expense[2]
            result += f"  - {expense[1]}: ${expense[2]:,.2f} ({expense[4]} payments, {expense[6]} frequency)\n"
        
        if current_category:
            result += f"  → Category total: ${category_total:,.2f}\n"
        
        # Add variance analysis if available
        cursor.execute("""
            SELECT 
                SUM(amount - budgeted_amount) as total_variance,
                COUNT(CASE WHEN amount > budgeted_amount THEN 1 END) as over_budget_count,
                COUNT(CASE WHEN amount < budgeted_amount THEN 1 END) as under_budget_count
            FROM expense_transactions
            WHERE budgeted_amount IS NOT NULL AND budgeted_amount > 0
        """)
        
        variance_data = cursor.fetchone()
        if variance_data and variance_data[0] is not None:
            result += f"\nBudget variance: ${variance_data[0]:,.2f}\n"
            result += f"Items over budget: {variance_data[1]}, under budget: {variance_data[2]}\n"
        
        return result
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving expense data: {e}")
        return f"Error retrieving expense data: {e}"

def call_ollama_optimized(prompt, system_message, config):
    """Call Ollama API with optimized configuration for better responses"""
    # Get Ollama config with fallback
    ollama_url = config.get("homelab_url") or get_config().get("ollama.laptop_url", "http://localhost:11434")
    timeout = get_config().get("ollama.timeout", 60)
    
    # Create messages array
    messages = []
    
    # Add system message
    if system_message:
        messages.append({"role": "system", "content": system_message})
    
    # Add the user prompt
    messages.append({"role": "user", "content": prompt})
    
    try:
        # Make the request to Ollama with optimized config
        response = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": config.get("model", "llama3.1:8b"),
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": config.get("temperature", 0.7),
                    "top_p": config.get("top_p", 0.9),
                    "top_k": config.get("options", {}).get("top_k", 40),
                    "repeat_penalty": config.get("options", {}).get("repeat_penalty", 1.1),
                    "presence_penalty": config.get("options", {}).get("presence_penalty", 0.1),
                    "frequency_penalty": config.get("options", {}).get("frequency_penalty", 0.2)
                }
            },
            timeout=timeout
        )
        
        # Check if request was successful
        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            current_app.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        current_app.logger.error(f"Error calling Ollama: {e}")
        return None

def call_ollama_with_enhanced_context(user_prompt, conversation_context, memory):
    """Enhanced Ollama call with optimized configuration and comprehensive medical billing context."""
    try:
        # Import the optimization manager
        from utils.ai_optimization_config import get_optimization_manager
        
        optimizer = get_optimization_manager()
        
        # Get optimized Ollama configuration
        ollama_config = optimizer.get_optimized_ollama_config(user_prompt)
        
        # Get optimized system prompt with conversation history
        conversation_history = []
        if conversation_context:
            # Parse conversation context into history format
            lines = conversation_context.strip().split('\n')
            for line in lines:
                if line.startswith('User: '):
                    conversation_history.append({'role': 'user', 'content': line[6:]})
                elif line.startswith('Ada: '):
                    conversation_history.append({'role': 'assistant', 'content': line[5:]})
        
        system_prompt = optimizer.get_enhanced_system_prompt(
            question_context=user_prompt,
            conversation_history=conversation_history
        )
        
        # Add critical data accuracy instructions
        system_prompt += """

## CRITICAL INSTRUCTIONS - DATA ACCURACY:
- ONLY use the data provided in the user's prompt
- NEVER make up numbers, amounts, or statistics
- If data is not provided, say "I don't have that specific data"
- ALWAYS cite the exact numbers from the provided data
- Do NOT create fictional expense totals or breakdowns

IMPORTANT: Use ONLY the data provided in the user's message. Do not invent or hallucinate any financial figures."""

        # Use optimized configuration for Ollama call
        response = call_ollama_optimized(user_prompt, system_prompt, ollama_config)
        
        if response:
            return response
        else:
            return "I'm having trouble processing that right now. Could you rephrase your question? I can help you analyze provider performance, revenue trends, payer relationships, or any other aspect of your medical billing data using your actual data."
            
    except Exception as e:
        current_app.logger.error(f"Error in enhanced Ollama call: {e}")
        # Fallback to regular call_ollama
        return call_ollama(user_prompt, system_prompt if 'system_prompt' in locals() else None)