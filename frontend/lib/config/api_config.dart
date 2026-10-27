/// EvidencIA — Configuración de la API
/// URL base del backend FastAPI. Las claves API nunca se almacenan aquí.
class ApiConfig {
  ApiConfig._(); // clase no instanciable

  /// URL base del backend. Cambiar a producción cuando corresponda.
  static const String baseUrl = 'http://localhost:8000';

  static const String searchEndpoint = '$baseUrl/api/v1/search';
  static const String searchPicoEndpoint = '$baseUrl/api/v1/search/pico';
  static const String synthesizeEndpoint = '$baseUrl/api/v1/synthesize';
  static const String healthEndpoint = '$baseUrl/health';
}
