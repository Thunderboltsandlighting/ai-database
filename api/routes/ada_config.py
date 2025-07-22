"""
Ada Configuration API Routes

This module provides API endpoints for managing Ada's memory, personality,
and custom instructions.
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest
from utils.ada_memory import AdaMemory, AdaPersonalityManager
import os

# Create Blueprint
ada_config_bp = Blueprint("ada_config", __name__)

# Initialize memory system
ada_memory = None


def get_ada_memory():
    """Get or initialize Ada memory system."""
    global ada_memory
    if ada_memory is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(base_dir, "ada_memory.db")
        ada_memory = AdaMemory(db_path)
    return ada_memory


@ada_config_bp.route("/personality", methods=["GET"])
def get_personality():
    """Get Ada's current personality settings."""
    try:
        memory = get_ada_memory()
        personality = memory.get_personality()
        return jsonify({"personality": personality, "status": "success"})
    except Exception as e:
        current_app.logger.error(f"Error retrieving personality: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/personality", methods=["POST"])
def update_personality():
    """Update Ada's personality settings."""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing request data")

        memory = get_ada_memory()
        personality_manager = AdaPersonalityManager(memory)

        updated = []
        errors = []

        # Handle specific updates
        if "communication_style" in data:
            style = data["communication_style"]
            if personality_manager.set_communication_style(style):
                updated.append(f"Communication style: {style}")
            else:
                errors.append(f"Invalid communication style: {style}")

        if "analysis_depth" in data:
            depth = data["analysis_depth"]
            if personality_manager.set_analysis_depth(depth):
                updated.append(f"Analysis depth: {depth}")
            else:
                errors.append(f"Invalid analysis depth: {depth}")

        if "proactive_suggestions" in data:
            proactive = data["proactive_suggestions"]
            personality_manager.enable_proactive_suggestions(proactive)
            status = "enabled" if proactive else "disabled"
            updated.append(f"Proactive suggestions: {status}")

        # Handle manual personality updates
        if "custom_updates" in data:
            for update in data["custom_updates"]:
                category = update.get("category")
                setting = update.get("setting")
                value = update.get("value")

                if category and setting and value:
                    if memory.update_personality(category, setting, value):
                        updated.append(f"{category}.{setting}: {value}")
                    else:
                        errors.append(f"Failed to update {category}.{setting}")

        return jsonify(
            {
                "updated": updated,
                "errors": errors,
                "status": "success" if updated else "warning",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error updating personality: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/instructions", methods=["GET"])
def get_instructions():
    """Get custom instructions."""
    try:
        category = request.args.get("category")
        memory = get_ada_memory()
        instructions = memory.get_custom_instructions(category=category)

        return jsonify({"instructions": instructions, "status": "success"})
    except Exception as e:
        current_app.logger.error(f"Error retrieving instructions: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/instructions", methods=["POST"])
def add_instruction():
    """Add a new custom instruction."""
    try:
        data = request.get_json()
        if not data or "instruction" not in data:
            raise BadRequest("Missing 'instruction' in request data")

        memory = get_ada_memory()
        instruction_id = memory.add_custom_instruction(
            category=data.get("category", "general"),
            instruction=data["instruction"],
            priority=data.get("priority", 5),
        )

        return jsonify(
            {
                "instruction_id": instruction_id,
                "message": "Instruction added successfully",
                "status": "success",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error adding instruction: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/instructions/<int:instruction_id>", methods=["DELETE"])
def delete_instruction(instruction_id):
    """Delete a custom instruction."""
    try:
        memory = get_ada_memory()
        # Deactivate instead of delete to preserve history
        conn = memory.conn if hasattr(memory, "conn") else None
        if not conn:
            import sqlite3

            conn = sqlite3.connect(memory.db_path)

        cursor = conn.execute(
            """
            UPDATE custom_instructions
            SET active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE instruction_id = ?
        """,
            (instruction_id,),
        )

        if cursor.rowcount > 0:
            conn.commit()
            return jsonify(
                {"message": "Instruction deactivated successfully", "status": "success"}
            )
        else:
            return jsonify({"error": "Instruction not found", "status": "error"}), 404

    except Exception as e:
        current_app.logger.error(f"Error deleting instruction: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/user-context", methods=["GET"])
def get_user_context():
    """Get user context information."""
    try:
        memory = get_ada_memory()
        context = memory.get_user_context()

        return jsonify({"context": context, "status": "success"})
    except Exception as e:
        current_app.logger.error(f"Error retrieving user context: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/user-context", methods=["POST"])
def update_user_context():
    """Update user context information."""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing request data")

        memory = get_ada_memory()
        success = memory.update_user_context(**data)

        if success:
            return jsonify(
                {"message": "User context updated successfully", "status": "success"}
            )
        else:
            return (
                jsonify({"error": "Failed to update user context", "status": "error"}),
                500,
            )

    except Exception as e:
        current_app.logger.error(f"Error updating user context: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/memories", methods=["GET"])
def get_memories():
    """Get stored memories."""
    try:
        memory_type = request.args.get("type")
        tags = request.args.getlist("tags")
        limit = int(request.args.get("limit", 20))
        min_importance = int(request.args.get("min_importance", 1))

        memory = get_ada_memory()
        memories = memory.retrieve_memories(
            memory_type=memory_type,
            tags=tags if tags else None,
            limit=limit,
            min_importance=min_importance,
        )

        return jsonify(
            {"memories": memories, "count": len(memories), "status": "success"}
        )

    except Exception as e:
        current_app.logger.error(f"Error retrieving memories: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/memories", methods=["POST"])
def store_memory():
    """Store a new memory."""
    try:
        data = request.get_json()
        if not data or "content" not in data:
            raise BadRequest("Missing 'content' in request data")

        memory = get_ada_memory()
        memory_id = memory.store_memory(
            memory_type=data.get("type", "insight"),
            content=data["content"],
            context=data.get("context"),
            importance=data.get("importance", 5),
            tags=data.get("tags"),
            expires_in_days=data.get("expires_in_days"),
        )

        return jsonify(
            {
                "memory_id": memory_id,
                "message": "Memory stored successfully",
                "status": "success",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error storing memory: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/system-prompt", methods=["GET"])
def get_system_prompt():
    """Get Ada's current system prompt with all personality and context."""
    try:
        conversation_context = request.args.get("conversation_context", "")

        memory = get_ada_memory()
        system_prompt = memory.build_system_prompt(conversation_context)

        return jsonify(
            {
                "system_prompt": system_prompt,
                "length": len(system_prompt),
                "status": "success",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error building system prompt: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/presets", methods=["GET"])
def get_personality_presets():
    """Get available personality presets."""
    presets = {
        "professional": {
            "name": "Professional",
            "description": "Formal, detailed, business-focused",
            "settings": {
                "communication_style": "professional",
                "analysis_depth": "detailed",
                "proactive_suggestions": True,
            },
        },
        "friendly": {
            "name": "Friendly Assistant",
            "description": "Warm, approachable, helpful",
            "settings": {
                "communication_style": "friendly",
                "analysis_depth": "standard",
                "proactive_suggestions": True,
            },
        },
        "technical": {
            "name": "Technical Expert",
            "description": "Technical focus, detailed analysis",
            "settings": {
                "communication_style": "technical",
                "analysis_depth": "expert",
                "proactive_suggestions": True,
            },
        },
        "concise": {
            "name": "Concise Assistant",
            "description": "Brief, direct responses",
            "settings": {
                "communication_style": "concise",
                "analysis_depth": "basic",
                "proactive_suggestions": False,
            },
        },
    }

    return jsonify({"presets": presets, "status": "success"})


@ada_config_bp.route("/presets/<preset_name>", methods=["POST"])
def apply_personality_preset(preset_name):
    """Apply a personality preset."""
    try:
        # Get the preset
        response = get_personality_presets()
        presets = response.get_json()["presets"]

        if preset_name not in presets:
            return (
                jsonify({"error": f"Unknown preset: {preset_name}", "status": "error"}),
                400,
            )

        preset = presets[preset_name]
        settings = preset["settings"]

        # Apply the settings
        memory = get_ada_memory()
        personality_manager = AdaPersonalityManager(memory)

        updated = []
        if "communication_style" in settings:
            style = settings["communication_style"]
            personality_manager.set_communication_style(style)
            updated.append(f"Communication style: {style}")

        if "analysis_depth" in settings:
            depth = settings["analysis_depth"]
            personality_manager.set_analysis_depth(depth)
            updated.append(f"Analysis depth: {depth}")

        if "proactive_suggestions" in settings:
            proactive = settings["proactive_suggestions"]
            personality_manager.enable_proactive_suggestions(proactive)
            status = "enabled" if proactive else "disabled"
            updated.append(f"Proactive suggestions: {status}")

        return jsonify(
            {
                "preset": preset_name,
                "applied_settings": updated,
                "message": f"Applied {preset['name']} personality preset",
                "status": "success",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error applying preset: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@ada_config_bp.route("/reset", methods=["POST"])
def reset_ada_config():
    """Reset Ada to default configuration."""
    try:
        memory = get_ada_memory()

        # Reinitialize the database to restore defaults
        memory.init_database()

        return jsonify(
            {"message": "Ada configuration reset to defaults", "status": "success"}
        )

    except Exception as e:
        current_app.logger.error(f"Error resetting Ada config: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500
