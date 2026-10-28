/// EvidencIA — Test del panel de vocabulario controlado y jerarquía de evidencia.
/// Verifica que el payload nuevo del backend (DeCS/MeSH + niveles) se
/// deserealiza y se muestra en la UI.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:evidencia/models/article.dart';
import 'package:evidencia/widgets/article_card.dart';
import 'package:evidencia/widgets/vocabulario_jerarquia_panel.dart';

Map<String, dynamic> _payload() => {
      'query': '("Diabetes Mellitus, Type 2"[MeSH Terms])',
      'total_encontrados': 69,
      'pregunta_clinica': 'En adultos con diabetes tipo 2, ¿la metformina reduce mortalidad?',
      'query_pubmed': '("Diabetes Mellitus, Type 2"[MeSH Terms]) AND Metformin[tiab]',
      'usado_ia': true,
      'prioridad_calidad': true,
      'niveles_consultados': ['ets', 'rs_ma', 'rct', 'obs'],
      'totales_por_nivel': {
        'ets': 0,
        'rs_ma': 18,
        'rct': 46,
        'obs': 5,
      },
      'distribucion_devueltos': {
        'rs_ma': 2,
        'rct': 1,
      },
      'terminos_clinicos': [
        {
          'entrada': 'diabetes tipo 2',
          'descriptor': 'Diabetes Mellitus, Type 2',
          'mesh_ui': 'D003924',
          'decs_nombre': 'Diabetes Mellitus Tipo 2',
          'fuente': 'mesh',
          'clausura': '"Diabetes Mellitus, Type 2"[MeSH Terms]',
        },
        {
          'entrada': 'gliflozina',
          'descriptor': '',
          'mesh_ui': '',
          'decs_nombre': '',
          'fuente': 'vacio',
          'clausura': 'gliflozina[tiab]',
        },
      ],
      'correcciones_vocabulario': [
        '"type 2 diabetes"[MeSH Terms] -> "Diabetes Mellitus, Type 2"[MeSH Terms]',
      ],
      'articulos': [
        {
          'pmid': '12345678',
          'titulo': 'Metformin and mortality: a systematic review and meta-analysis',
          'autores': [
            {'nombre': 'Perez J', 'afiliacion': null}
          ],
          'revista': 'BMJ',
          'año': 2024,
          'abstract': 'Resumen del estudio.',
          'doi': '10.1000/bmj.1234',
          'url_pubmed': 'https://pubmed.ncbi.nlm.nih.gov/12345678/',
          'revista_iso': 'BMJ',
          'tipos_publicacion': ['Meta-Analysis', 'Journal Article'],
          'mesh_descriptores': ['Diabetes Mellitus, Type 2', 'Metformin'],
          'afiliaciones': '',
          'nivel_evidencia': 'rs_ma',
          'nivel_etiqueta': 'Revisión sistemática / Metaanálisis',
          'nivel_orden': 2,
          'senal_nivel': 'Tipo de publicación: Meta-Analysis',
          'recuperado_por_nivel': 'rs_ma',
        },
      ],
    };

void main() {
  group('Deserialización del payload DeCS/MeSH + jerarquía', () {
    test('SearchResponse lee términos, niveles y correcciones', () {
      final r = SearchResponse.fromJson(_payload());

      expect(r.prioridadCalidad, isTrue);
      expect(r.nivelesConsultados, ['ets', 'rs_ma', 'rct', 'obs']);
      expect(r.totalesPorNivel['rs_ma'], 18);
      expect(r.distribucionDevueltos['rct'], 1);
      expect(r.correccionesVocabulario, hasLength(1));

      final resuelto = r.terminosClinicos.first;
      expect(resuelto.descriptor, 'Diabetes Mellitus, Type 2');
      expect(resuelto.meshUi, 'D003924');
      expect(resuelto.fuenteEtiqueta, 'MeSH');
      expect(r.terminosClinicos.last.fuenteEtiqueta, 'sin resolver');
    });

    test('Article conserva nivel de evidencia y metadatos técnicos', () {
      final a = SearchResponse.fromJson(_payload()).articulos.single;

      expect(a.nivelEvidencia, 'rs_ma');
      expect(a.nivelOrden, 2);
      expect(a.nivelEtiqueta, 'Revisión sistemática / Metaanálisis');
      expect(a.senalNivel, contains('Meta-Analysis'));
      expect(a.tiposPublicacion, contains('Meta-Analysis'));
      expect(a.meshDescriptores, contains('Metformin'));
      expect(a.revistaIso, 'BMJ');
      expect(a.recuperadoPorNivel, 'rs_ma');
    });

    test('un payload antiguo (sin campos nuevos) no rompe el parseo', () {
      final r = SearchResponse.fromJson({
        'query': 'metformin',
        'total_encontrados': 3,
        'articulos': [
          {
            'pmid': '1',
            'titulo': 'T',
            'autores': <Map<String, dynamic>>[],
            'revista': 'R',
            'año': 2020,
            'abstract': null,
            'doi': null,
            'url_pubmed': 'https://pubmed.ncbi.nlm.nih.gov/1/',
          },
        ],
      });

      expect(r.articulos.single.nivelOrden, 5);
      expect(r.terminosClinicos, isEmpty);
      expect(r.totalesPorNivel, isEmpty);
      expect(r.prioridadCalidad, isFalse);
    });
  });

  group('Renderizado', () {
    testWidgets('el panel muestra descriptores, origen y conteos por nivel',
        (tester) async {
      final r = SearchResponse.fromJson(_payload());

      await tester.binding.setSurfaceSize(const Size(1200, 1400));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: VocabularioYJerarquiaPanel(result: r),
            ),
          ),
        ),
      );

      expect(find.text('Diabetes Mellitus, Type 2'), findsOneWidget);
      expect(find.text('D003924'), findsOneWidget);
      expect(find.text('sin descriptor'), findsOneWidget);
      expect(find.textContaining('N1 · ETS / HTA'), findsOneWidget);
      expect(find.textContaining('N2 · RS / Metaanálisis'), findsOneWidget);
      expect(find.text('2 de 18'), findsOneWidget);
      expect(find.textContaining('Descriptores corregidos'), findsOneWidget);
    });

    testWidgets('el panel se oculta cuando el backend no envía nada nuevo',
        (tester) async {
      final r = SearchResponse.fromJson({
        'query': 'q',
        'total_encontrados': 0,
        'articulos': <Map<String, dynamic>>[],
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: VocabularioYJerarquiaPanel(result: r),
          ),
        ),
      );

      expect(find.byType(Card), findsNothing);
    });

    testWidgets('la tarjeta muestra el badge del nivel de evidencia',
        (tester) async {
      final a = SearchResponse.fromJson(_payload()).articulos.single;

      await tester.binding.setSurfaceSize(const Size(1000, 1200));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ArticleCard(
              article: a,
              isSelected: false,
              onToggle: () {},
            ),
          ),
        ),
      );

      expect(find.textContaining('· N2'), findsOneWidget);
      expect(find.textContaining('Tipo de publicación: Meta-Analysis'), findsOneWidget);
      expect(find.textContaining('MeSH: Diabetes Mellitus, Type 2'), findsOneWidget);
    });
  });
}
