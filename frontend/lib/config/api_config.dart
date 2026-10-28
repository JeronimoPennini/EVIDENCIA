/// EvidencIA — Configuración de la API
/// URL base del backend FastAPI. Las claves API nunca se almacenan aquí.
class ApiConfig {
  ApiConfig._(); // clase no instanciable

  /// URL base del backend, **sin barra final**.
  ///
  /// En desarrollo no hay que tocar nada: apunta a `http://localhost:8000`.
  /// En producción se fija al compilar, sin modificar este archivo:
  ///
  ///   flutter build web  --release --dart-define=API_BASE_URL=https://<host>.onrender.com
  ///   flutter run -d chrome --dart-define=API_BASE_URL=https://<host>.onrender.com
  ///
  /// Las claves API siguen viviendo solo en el backend; acá va únicamente la URL pública.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// True cuando corre contra el backend local (útil para mensajes de error).
  static bool get esLocal =>
      baseUrl.contains('localhost') || baseUrl.contains('127.0.0.1');

  static const String searchEndpoint = '$baseUrl/api/v1/search';
  static const String searchPicoEndpoint = '$baseUrl/api/v1/search/pico';
  static const String synthesizeEndpoint = '$baseUrl/api/v1/synthesize';
  static const String healthEndpoint = '$baseUrl/health';
}
