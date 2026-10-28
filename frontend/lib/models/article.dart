class Author {
  final String nombre;
  final String? afiliacion;

  const Author({required this.nombre, this.afiliacion});

  factory Author.fromJson(Map<String, dynamic> json) => Author(
        nombre: json['nombre'] as String,
        afiliacion: json['afiliacion'] as String?,
      );
}

class TerminoClinico {
  final String entrada;
  final String descriptor;
  final String meshUi;
  final String decsNombre;
  final String fuente;
  final String clausura;

  const TerminoClinico({
    required this.entrada,
    this.descriptor = '',
    this.meshUi = '',
    this.decsNombre = '',
    this.fuente = 'diccionario',
    this.clausura = '',
  });

  factory TerminoClinico.fromJson(Map<String, dynamic> json) => TerminoClinico(
        entrada: json['entrada'] as String? ?? '',
        descriptor: json['descriptor'] as String? ?? '',
        meshUi: json['mesh_ui'] as String? ?? '',
        decsNombre: json['decs_nombre'] as String? ?? '',
        fuente: json['fuente'] as String? ?? 'diccionario',
        clausura: json['clausura'] as String? ?? '',
      );

  /// Nombre curto para mostrar: descriptor resuelto o la entrada original.
  String get etiqueta => descriptor.isNotEmpty ? descriptor : entrada;

  /// Etiqueta de origen legible en español.
  String get fuenteEtiqueta {
    switch (fuente) {
      case 'decs':
        return 'DeCS';
      case 'mesh':
        return 'MeSH';
      case 'diccionario':
        return 'diccionario';
      default:
        return 'sin resolver';
    }
  }
}

class Article {
  final String pmid;
  final String titulo;
  final List<Author> autores;
  final String? revista;
  final int? anio;
  final String? abstract;
  final String? doi;
  final String urlPubmed;
  final String revistaIso;
  final List<String> tiposPublicacion;
  final List<String> meshDescriptores;
  final String nivelEvidencia;
  final String nivelEtiqueta;
  final int nivelOrden;
  final String senalNivel;
  final String recuperadoPorNivel;

  const Article({
    required this.pmid,
    required this.titulo,
    required this.autores,
    this.revista,
    this.anio,
    this.abstract,
    this.doi,
    required this.urlPubmed,
    this.revistaIso = '',
    this.tiposPublicacion = const [],
    this.meshDescriptores = const [],
    this.nivelEvidencia = 'otros',
    this.nivelEtiqueta = 'Otro tipo de estudio',
    this.nivelOrden = 5,
    this.senalNivel = '',
    this.recuperadoPorNivel = '',
  });

  factory Article.fromJson(Map<String, dynamic> json) => Article(
        pmid: json['pmid'] as String,
        titulo: json['titulo'] as String,
        autores: (json['autores'] as List<dynamic>)
            .map((a) => Author.fromJson(a as Map<String, dynamic>))
            .toList(),
        revista: json['revista'] as String?,
        anio: json['año'] as int? ?? json['anio'] as int?,
        abstract: json['abstract'] as String?,
        doi: json['doi'] as String?,
        urlPubmed: json['url_pubmed'] as String? ?? '',
        revistaIso: json['revista_iso'] as String? ?? '',
        tiposPublicacion: _cadenaLista(json['tipos_publicacion']),
        meshDescriptores: _cadenaLista(json['mesh_descriptores']),
        nivelEvidencia: json['nivel_evidencia'] as String? ?? 'otros',
        nivelEtiqueta:
            json['nivel_etiqueta'] as String? ?? 'Otro tipo de estudio',
        nivelOrden: (json['nivel_orden'] as num?)?.toInt() ?? 5,
        senalNivel: json['senal_nivel'] as String? ?? '',
        recuperadoPorNivel: json['recuperado_por_nivel'] as String? ?? '',
      );

  static List<String> _cadenaLista(Object? valor) {
    if (valor is List) {
      return valor.map((e) => e.toString()).where((e) => e.isNotEmpty).toList();
    }
    return const [];
  }

  String get autoresCortados {
    if (autores.isEmpty) return 'Sin autores';
    if (autores.length <= 3) return autores.map((a) => a.nombre).join(', ');
    return '${autores.take(3).map((a) => a.nombre).join(', ')} et al.';
  }
}

class SearchResponse {
  final String query;
  final int totalEncontrados;
  final List<Article> articulos;
  final String? preguntaClinica;
  final String? queryPubmed;
  final bool usadoIa;
  final List<TerminoClinico> terminosClinicos;
  final List<String> correccionesVocabulario;
  final List<String> nivelesConsultados;
  final Map<String, int> totalesPorNivel;
  final Map<String, int> distribucionDevueltos;
  final bool prioridadCalidad;
  final String? avisoIa;

  const SearchResponse({
    required this.query,
    required this.totalEncontrados,
    required this.articulos,
    this.preguntaClinica,
    this.queryPubmed,
    this.usadoIa = false,
    this.terminosClinicos = const [],
    this.correccionesVocabulario = const [],
    this.nivelesConsultados = const [],
    this.totalesPorNivel = const {},
    this.distribucionDevueltos = const {},
    this.prioridadCalidad = false,
    this.avisoIa,
  });

  factory SearchResponse.fromJson(Map<String, dynamic> json) => SearchResponse(
        query: json['query'] as String,
        totalEncontrados: json['total_encontrados'] as int,
        articulos: (json['articulos'] as List<dynamic>)
            .map((a) => Article.fromJson(a as Map<String, dynamic>))
            .toList(),
        preguntaClinica: json['pregunta_clinica'] as String?,
        queryPubmed: json['query_pubmed'] as String?,
        usadoIa: json['usado_ia'] as bool? ?? false,
        terminosClinicos: (json['terminos_clinicos'] as List<dynamic>? ?? [])
            .map((t) => TerminoClinico.fromJson(t as Map<String, dynamic>))
            .toList(),
        correccionesVocabulario: (json['correcciones_vocabulario'] as List<dynamic>? ?? [])
            .map((e) => e.toString())
            .toList(),
        nivelesConsultados: (json['niveles_consultados'] as List<dynamic>? ?? [])
            .map((e) => e.toString())
            .toList(),
        totalesPorNivel: _enterosPorClave(json['totales_por_nivel']),
        distribucionDevueltos: _enterosPorClave(json['distribucion_devueltos']),
        prioridadCalidad: json['prioridad_calidad'] as bool? ?? false,
        avisoIa: json['aviso_ia'] as String?,
      );

  static Map<String, int> _enterosPorClave(Object? valor) {
    if (valor is Map) {
      return <String, int>{
        for (final e in valor.entries) e.key.toString(): (e.value as num?)?.toInt() ?? 0,
      };
    }
    return const {};
  }
}
