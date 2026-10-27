class Author {
  final String nombre;
  final String? afiliacion;

  const Author({required this.nombre, this.afiliacion});

  factory Author.fromJson(Map<String, dynamic> json) => Author(
        nombre: json['nombre'] as String,
        afiliacion: json['afiliacion'] as String?,
      );
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

  const Article({
    required this.pmid,
    required this.titulo,
    required this.autores,
    this.revista,
    this.anio,
    this.abstract,
    this.doi,
    required this.urlPubmed,
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
      );

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

  const SearchResponse({
    required this.query,
    required this.totalEncontrados,
    required this.articulos,
    this.preguntaClinica,
    this.queryPubmed,
    this.usadoIa = false,
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
      );
}
