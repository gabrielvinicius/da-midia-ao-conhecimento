# src/shared/infrastructure/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider

# Disable Jaeger for now to avoid dependency issues
# from opentelemetry.exporter.jaeger.thrift import JaegerExporter
# from opentelemetry.sdk.trace.export import BatchSpanProcessor

def configure_tracer(service_name: str):
    """Configures the global tracer for the application."""
    # Set the service name for all traces
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })

    # Initialize the TracerProvider with the resource
    provider = TracerProvider(resource=resource)

    # Set the configured provider as the global tracer provider
    trace.set_tracer_provider(provider)

    print(f"✅ OpenTelemetry tracing configured for service '{service_name}' (Jaeger disabled)")

    return trace.get_tracer(__name__)
