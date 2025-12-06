"""
Módulo para gerenciamento de métricas Prometheus compartilhadas entre diferentes contextos
(FastAPI e Celery) para evitar duplicação de métricas.
"""
from typing import Dict, Optional
from threading import Lock

from prometheus_client import Counter, Histogram, Gauge, REGISTRY, CollectorRegistry


class SharedPrometheusMetrics:
    """
    Singleton para gerenciamento de métricas Prometheus que podem ser compartilhadas
    entre diferentes contextos (API e Celery) para evitar duplicação.
    """
    _instance = None
    _lock = Lock()
    
    # Dicionários para armazenar métricas já registradas
    _counters: Dict[str, Counter] = {}
    _histograms: Dict[str, Histogram] = {}
    _gauges: Dict[str, Gauge] = {}
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Verificar novamente dentro do lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            self._initialized = True

    def get_transcription_operation_counter(self) -> Counter:
        """Obtém ou cria o contador de operações de transcrição."""
        metric_name = 'transcription_operations_total'
        if metric_name not in self._counters:
            try:
                # Tenta registrar a nova métrica
                self._counters[metric_name] = Counter(
                    metric_name,
                    'Total number of transcription operations',
                    ['operation', 'provider', 'status']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._counters[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Counter as NoOpCounter
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def inc(self):
                                    pass
                            return NoOpMetric()
                    self._counters[metric_name] = NoOpMetrics()
        return self._counters[metric_name]

    def get_transcription_operation_duration(self) -> Histogram:
        """Obtém ou cria o histograma de duração de operações de transcrição."""
        metric_name = 'transcription_operation_duration_seconds'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Duration of transcription operations in seconds',
                    ['operation', 'provider']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_transcription_input_audio_length(self) -> Histogram:
        """Obtém ou cria o histograma de comprimento de áudio de entrada."""
        metric_name = 'transcription_input_audio_length_seconds'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Length of input audio in seconds',
                    ['provider']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_transcription_output_text_length(self) -> Histogram:
        """Obtém ou cria o histograma de comprimento de texto de saída."""
        metric_name = 'transcription_output_text_length_chars'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Length of output text in characters',
                    ['provider']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_transcription_active_operations(self) -> Gauge:
        """Obtém ou cria o gauge de operações ativas de transcrição."""
        metric_name = 'transcription_active_operations'
        if metric_name not in self._gauges:
            try:
                # Tenta registrar a nova métrica
                self._gauges[metric_name] = Gauge(
                    metric_name,
                    'Number of active transcription operations',
                    ['provider']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._gauges[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Gauge as NoOpGauge
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def inc(self):
                                    pass
                                def dec(self):
                                    pass
                            return NoOpMetric()
                    self._gauges[metric_name] = NoOpMetrics()
        return self._gauges[metric_name]

    def get_video_processing_operations_total(self):
        """Obtém ou cria o contador de operações de processamento de vídeo."""
        metric_name = 'video_processing_operations_total'
        if metric_name not in self._counters:
            try:
                # Tenta registrar a nova métrica
                self._counters[metric_name] = Counter(
                    metric_name,
                    'Total number of video processing operations',
                    ['operation', 'status'],
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._counters[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Counter as NoOpCounter
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def inc(self):
                                    pass
                            return NoOpMetric()
                    self._counters[metric_name] = NoOpMetrics()
        return self._counters[metric_name]

    def get_video_processing_duration_seconds(self):
        """Obtém ou cria o histograma de duração de operações de processamento de vídeo."""
        metric_name = 'video_processing_operation_duration_seconds'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Duration of video processing operations',
                    ['operation'],
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    # Text analysis metrics
    def get_text_analysis_operations_total(self):
        metric_name = 'text_analysis_operations_total'
        if metric_name not in self._counters:
            try:
                self._counters[metric_name] = Counter(
                    metric_name,
                    'Total number of text analysis operations',
                    ['operation', 'provider', 'status', 'media_id', 'user_id'],
                )
            except ValueError:
                for collector in REGISTRY._collector_to_names.keys():
                    if getattr(collector, '_name', None) == metric_name:
                        self._counters[metric_name] = collector
                        break
                else:
                    class NoOp:
                        def labels(self, **_labels):
                            class _M:
                                def inc(self):
                                    pass
                            return _M()
                    self._counters[metric_name] = NoOp()
        return self._counters[metric_name]

    def get_text_analysis_duration_seconds(self):
        metric_name = 'text_analysis_operation_duration_seconds'
        if metric_name not in self._histograms:
            try:
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Duration of text analysis operations in seconds',
                    ['operation', 'provider', 'media_id', 'user_id', 'status'],
                )
            except ValueError:
                for collector in REGISTRY._collector_to_names.keys():
                    if getattr(collector, '_name', None) == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    class NoOp:
                        def labels(self, **_labels):
                            class _M:
                                def observe(self, _v):
                                    pass
                            return _M()
                    self._histograms[metric_name] = NoOp()
        return self._histograms[metric_name]

    def get_video_processing_input_file_size_bytes(self):
        """Obtém ou cria o histograma de tamanho de arquivos de entrada de processamento de vídeo."""
        metric_name = 'video_processing_input_file_size_bytes'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Size of video files processed',
                    ['operation'],
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_topic_modeling_operations_total(self):
        """Obtém ou cria o contador de operações de modelagem de tópicos."""
        metric_name = 'topic_modeling_operations_total'
        if metric_name not in self._counters:
            try:
                # Tenta registrar a nova métrica
                self._counters[metric_name] = Counter(
                    metric_name,
                    'Total number of topic modeling operations',
                    ['operation', 'provider', 'status']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._counters[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Counter as NoOpCounter
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def inc(self):
                                    pass
                            return NoOpMetric()
                    self._counters[metric_name] = NoOpMetrics()
        return self._counters[metric_name]

    def get_topic_modeling_operation_duration_seconds(self):
        """Obtém ou cria o histograma de duração de operações de modelagem de tópicos."""
        metric_name = 'topic_modeling_operation_duration_seconds'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Duration of topic modeling operations in seconds',
                    ['operation', 'provider']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_topic_modeling_input_text_length_chars(self):
        """Obtém ou cria o histograma de comprimento de texto de entrada para modelagem de tópicos."""
        metric_name = 'topic_modeling_input_text_length_chars'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Length of input text in characters',
                    ['provider']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_topic_modeling_num_topics(self):
        """Obtém ou cria o histograma de número de tópicos identificados."""
        metric_name = 'topic_modeling_num_topics'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Number of topics identified',
                    ['provider']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_topic_modeling_active_operations(self):
        """Obtém ou cria o gauge de operações ativas de modelagem de tópicos."""
        metric_name = 'topic_modeling_active_operations'
        if metric_name not in self._gauges:
            try:
                # Tenta registrar a nova métrica
                self._gauges[metric_name] = Gauge(
                    metric_name,
                    'Number of active topic modeling operations',
                    ['provider']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._gauges[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Gauge as NoOpGauge
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def inc(self):
                                    pass
                                def dec(self):
                                    pass
                            return NoOpMetric()
                    self._gauges[metric_name] = NoOpMetrics()
        return self._gauges[metric_name]

    def get_sentiment_analysis_events_total(self):
        """Obtém ou cria o contador de eventos de análise de sentimento."""
        metric_name = 'sentiment_analysis_events_total'
        if metric_name not in self._counters:
            try:
                # Tenta registrar a nova métrica
                self._counters[metric_name] = Counter(
                    metric_name,
                    "Total number of sentiment analysis events emitted.",
                    labelnames=("metric",),
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._counters[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Counter as NoOpCounter
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def inc(self):
                                    pass
                            return NoOpMetric()
                    self._counters[metric_name] = NoOpMetrics()
        return self._counters[metric_name]

    def get_sentiment_analysis_processing_seconds(self):
        """Obtém ou cria o histograma de processamento de análise de sentimento."""
        metric_name = 'sentiment_analysis_processing_seconds'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    "Observed processing time for sentiment analysis operations.",
                    labelnames=("metric",),
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_text_processing_operations_total(self):
        """Obtém ou cria o contador de operações de processamento de texto."""
        metric_name = 'text_processing_operations_total'
        if metric_name not in self._counters:
            try:
                # Tenta registrar a nova métrica
                self._counters[metric_name] = Counter(
                    metric_name,
                    'Total number of text processing operations',
                    ['operation', 'format_type', 'status']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._counters[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Counter as NoOpCounter
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def inc(self):
                                    pass
                            return NoOpMetric()
                    self._counters[metric_name] = NoOpMetrics()
        return self._counters[metric_name]

    def get_text_processing_operation_duration_seconds(self):
        """Obtém ou cria o histograma de duração de operações de processamento de texto."""
        metric_name = 'text_processing_operation_duration_seconds'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Duration of text processing operations in seconds',
                    ['operation', 'format_type']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_text_processing_file_size_bytes(self):
        """Obtém ou cria o histograma de tamanho de arquivos processados de texto."""
        metric_name = 'text_processing_file_size_bytes'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Size of processed files in bytes',
                    ['format_type']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_text_processing_text_length_chars(self):
        """Obtém ou cria o histograma de comprimento de texto extraído."""
        metric_name = 'text_processing_text_length_chars'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Length of extracted text in characters',
                    ['format_type']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_text_processing_extraction_ratio(self):
        """Obtém ou cria o histograma de razão de extração de texto."""
        metric_name = 'text_processing_extraction_ratio'
        if metric_name not in self._histograms:
            try:
                # Tenta registrar a nova métrica
                self._histograms[metric_name] = Histogram(
                    metric_name,
                    'Ratio of extracted text length to file size',
                    ['format_type']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._histograms[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Histogram as NoOpHistogram
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def observe(self, value):
                                    pass
                            return NoOpMetric()
                    self._histograms[metric_name] = NoOpMetrics()
        return self._histograms[metric_name]

    def get_text_processing_active_operations(self):
        """Obtém ou cria o gauge de operações ativas de processamento de texto."""
        metric_name = 'text_processing_active_operations'
        if metric_name not in self._gauges:
            try:
                # Tenta registrar a nova métrica
                self._gauges[metric_name] = Gauge(
                    metric_name,
                    'Number of active text processing operations',
                    ['format_type']
                )
            except ValueError:
                # Se já estiver registrada, pegar do registry
                for collector in REGISTRY._collector_to_names.keys():
                    if hasattr(collector, '_name') and collector._name == metric_name:
                        self._gauges[metric_name] = collector
                        break
                else:
                    # Se não encontrar, criar uma métrica sem registrar (noop)
                    from prometheus_client import Gauge as NoOpGauge
                    class NoOpMetrics:
                        def labels(self, **labels):
                            class NoOpMetric:
                                def inc(self):
                                    pass
                                def dec(self):
                                    pass
                            return NoOpMetric()
                    self._gauges[metric_name] = NoOpMetrics()
        return self._gauges[metric_name]


# Instância global compartilhada
shared_metrics = SharedPrometheusMetrics()
