"""
Unified templates - eliminating template duplication
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

class TemplateType(str, Enum):
    """Template types"""
    EMAIL = "email"
    NOTIFICATION = "notification"
    PROMPT = "prompt"
    RESPONSE = "response"

@dataclass
class Template:
    """Unified template structure"""
    name: str
    type: TemplateType
    content: str
    variables: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []
        if self.metadata is None:
            self.metadata = {}

class UnifiedTemplateEngine:
    """Single template engine for all modules"""
    
    def __init__(self):
        self._templates: Dict[str, Template] = {}
        self._setup_default_templates()
    
    def _setup_default_templates(self):
        """Setup default templates for all modules"""
        
        # Notification templates
        self.register_template(Template(
            name="processing_started",
            type=TemplateType.NOTIFICATION,
            content="{entity_type} processing started for {entity_id}",
            variables=["entity_type", "entity_id"]
        ))
        
        self.register_template(Template(
            name="processing_completed",
            type=TemplateType.NOTIFICATION,
            content="{entity_type} processing completed successfully for {entity_id}",
            variables=["entity_type", "entity_id"]
        ))
        
        self.register_template(Template(
            name="processing_failed",
            type=TemplateType.NOTIFICATION,
            content="{entity_type} processing failed for {entity_id}: {error}",
            variables=["entity_type", "entity_id", "error"]
        ))
        
        # Email templates
        self.register_template(Template(
            name="transcription_completed_email",
            type=TemplateType.EMAIL,
            content="""
            <h2>Transcription Completed</h2>
            <p>Your transcription for media {media_id} has been completed.</p>
            <p>Text length: {text_length} characters</p>
            <p>Language: {language}</p>
            """,
            variables=["media_id", "text_length", "language"]
        ))
        
        self.register_template(Template(
            name="summary_completed_email",
            type=TemplateType.EMAIL,
            content="""
            <h2>Summary Completed</h2>
            <p>Your summary for media {media_id} has been completed.</p>
            <p>Summary length: {summary_length} characters</p>
            <p>Provider: {provider}</p>
            """,
            variables=["media_id", "summary_length", "provider"]
        ))
        
        # Response templates
        self.register_template(Template(
            name="api_success_response",
            type=TemplateType.RESPONSE,
            content='{"success": true, "data": {data}, "message": "{message}"}',
            variables=["data", "message"]
        ))
        
        self.register_template(Template(
            name="api_error_response",
            type=TemplateType.RESPONSE,
            content='{"success": false, "error": "{error}", "code": "{code}"}',
            variables=["error", "code"]
        ))
    
    def register_template(self, template: Template):
        """Register a template"""
        self._templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[Template]:
        """Get template by name"""
        return self._templates.get(name)
    
    def render_template(self, name: str, **variables) -> str:
        """Render template with variables"""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")
        
        try:
            return template.content.format(**variables)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise ValueError(f"Missing variable '{missing_var}' for template '{name}'")
    
    def list_templates(self, template_type: Optional[TemplateType] = None) -> List[str]:
        """List available templates"""
        if template_type:
            return [
                name for name, template in self._templates.items()
                if template.type == template_type
            ]
        return list(self._templates.keys())
    
    def get_template_variables(self, name: str) -> List[str]:
        """Get required variables for a template"""
        template = self.get_template(name)
        return template.variables if template else []

# Global template engine
template_engine = UnifiedTemplateEngine()

# Convenience functions
def render_notification(entity_type: str, status: str, **kwargs) -> str:
    """Render notification template"""
    template_name = f"processing_{status}"
    return template_engine.render_template(
        template_name,
        entity_type=entity_type,
        **kwargs
    )

def render_email(template_name: str, **kwargs) -> str:
    """Render email template"""
    return template_engine.render_template(template_name, **kwargs)

def render_response(success: bool, **kwargs) -> str:
    """Render API response template"""
    template_name = "api_success_response" if success else "api_error_response"
    return template_engine.render_template(template_name, **kwargs)
