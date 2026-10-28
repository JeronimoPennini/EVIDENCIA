import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/search_provider.dart';
import '../providers/synthesis_provider.dart';
import '../widgets/article_card.dart';
import '../widgets/vocabulario_jerarquia_panel.dart';
import 'synthesis_screen.dart';

enum SearchMode { pico, libre }

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  SearchMode _mode = SearchMode.pico;

  // Controladores PICO
  final _poblacionController = TextEditingController();
  final _intervencionController = TextEditingController();
  final _comparacionController = TextEditingController();
  final _outcomeController = TextEditingController();

  // Controladores Búsqueda Libre
  final _queryController = TextEditingController();
  final _preguntaLibreController = TextEditingController();

  // Filtros
  int _maxResults = 10;
  String _filtroEstudio = 'all'; // 'all', 'rct', 'systematic_review'
  String _filtroFecha = 'all'; // 'all', '5_years', '10_years'
  bool _optimizarConIa = true;
  bool _usarVocabulario = true;
  bool _priorizarCalidad = true;
  bool _mostrarQueryDetalle = false;

  @override
  void initState() {
    super.initState();
    _poblacionController.addListener(_onPicoChanged);
    _intervencionController.addListener(_onPicoChanged);
    _comparacionController.addListener(_onPicoChanged);
    _outcomeController.addListener(_onPicoChanged);
  }

  @override
  void dispose() {
    _poblacionController.removeListener(_onPicoChanged);
    _intervencionController.removeListener(_onPicoChanged);
    _comparacionController.removeListener(_onPicoChanged);
    _outcomeController.removeListener(_onPicoChanged);

    _poblacionController.dispose();
    _intervencionController.dispose();
    _comparacionController.dispose();
    _outcomeController.dispose();
    _queryController.dispose();
    _preguntaLibreController.dispose();
    super.dispose();
  }

  void _onPicoChanged() {
    setState(() {}); // Actualiza la vista previa de la pregunta clínica
  }

  String get _preguntaClinicaGenerada {
    final p = _poblacionController.text.trim();
    final i = _intervencionController.text.trim();
    final c = _comparacionController.text.trim();
    final o = _outcomeController.text.trim();

    if (p.isEmpty && i.isEmpty && o.isEmpty) {
      return '';
    }

    final comp = c.isNotEmpty ? ' en comparación con $c' : '';
    return 'En ${p.isEmpty ? "[Población]" : p}, ¿cuál es el efecto de ${i.isEmpty ? "[Intervención]" : i}$comp sobre ${o.isEmpty ? "[Desenlace]" : o}?';
  }

  void _cargarEjemplo({
    required String p,
    required String i,
    required String c,
    required String o,
  }) {
    _poblacionController.text = p;
    _intervencionController.text = i;
    _comparacionController.text = c;
    _outcomeController.text = o;
  }

  void _limpiarFormulario() {
    _poblacionController.clear();
    _intervencionController.clear();
    _comparacionController.clear();
    _outcomeController.clear();
    _queryController.clear();
    _preguntaLibreController.clear();
    ref.read(searchProvider.notifier).limpiar();
  }

  (String?, String?) _calcularRangoFechas() {
    final ahora = DateTime.now();
    if (_filtroFecha == '5_years') {
      final desde = DateTime(ahora.year - 5, ahora.month, ahora.day);
      return (
        '${desde.year}/${desde.month.toString().padLeft(2, '0')}/${desde.day.toString().padLeft(2, '0')}',
        '${ahora.year}/${ahora.month.toString().padLeft(2, '0')}/${ahora.day.toString().padLeft(2, '0')}'
      );
    } else if (_filtroFecha == '10_years') {
      final desde = DateTime(ahora.year - 10, ahora.month, ahora.day);
      return (
        '${desde.year}/${desde.month.toString().padLeft(2, '0')}/${desde.day.toString().padLeft(2, '0')}',
        '${ahora.year}/${ahora.month.toString().padLeft(2, '0')}/${ahora.day.toString().padLeft(2, '0')}'
      );
    }
    return (null, null);
  }

  void _ejecutarBusqueda() {
    final (dateFrom, dateTo) = _calcularRangoFechas();

    if (_mode == SearchMode.pico) {
      final p = _poblacionController.text.trim();
      final i = _intervencionController.text.trim();
      final o = _outcomeController.text.trim();

      if (p.length < 2 || i.length < 2 || o.length < 2) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Por favor completa al menos Población (P), Intervención (I) y Desenlace (O).'),
          ),
        );
        return;
      }

      ref.read(searchProvider.notifier).buscarPico(
            poblacion: p,
            intervencion: i,
            comparacion: _comparacionController.text.trim(),
            outcome: o,
            filtroEstudio: _filtroEstudio,
            maxResults: _maxResults,
            dateFrom: dateFrom,
            dateTo: dateTo,
            optimizarConIa: _optimizarConIa,
            usarVocabulario: _usarVocabulario,
            priorizarCalidad: _priorizarCalidad,
          );
    } else {
      final query = _queryController.text.trim();
      if (query.length < 3) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Ingresa al menos 3 caracteres para buscar.')),
        );
        return;
      }
      ref.read(searchProvider.notifier).buscar(
            query: query,
            maxResults: _maxResults,
          );
      final pregunta = _preguntaLibreController.text.trim();
      if (pregunta.isNotEmpty) {
        ref.read(searchProvider.notifier).setPreguntaClinica(pregunta);
      }
    }
  }

  void _irASintesis(List<String> pmids) {
    final searchState = ref.read(searchProvider);
    String pregunta = searchState.preguntaClinica ?? '';

    if (pregunta.isEmpty) {
      if (_mode == SearchMode.pico) {
        pregunta = _preguntaClinicaGenerada;
      } else {
        pregunta = _preguntaLibreController.text.trim();
        if (pregunta.isEmpty) {
          pregunta = _queryController.text.trim();
        }
      }
    }

    if (pregunta.length < 8) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Se requiere una pregunta clínica para sintetizar.')),
      );
      return;
    }

    ref.read(synthesisProvider.notifier).sintetizar(
          pmids: pmids,
          preguntaClinica: pregunta,
        );

    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const SynthesisScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final searchState = ref.watch(searchProvider);
    final selectedPmids = searchState.selectedPmids.toList();

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'EvidencIA',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.onPrimaryContainer,
                ),
              ),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Búsqueda y Síntesis de Evidencia Médica',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.normal),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        actions: [
          if (selectedPmids.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: FilledButton.icon(
                onPressed: () => _irASintesis(selectedPmids),
                icon: const Icon(Icons.auto_awesome, size: 18),
                label: Text('Sintetizar (${selectedPmids.length})'),
              ),
            ),
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth > 950;

          final searchContent = Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Selector de modo
              SegmentedButton<SearchMode>(
                segments: const [
                  ButtonSegment(
                    value: SearchMode.pico,
                    icon: Icon(Icons.psychology_alt_outlined),
                    label: Text('Pregunta PICO'),
                  ),
                  ButtonSegment(
                    value: SearchMode.libre,
                    icon: Icon(Icons.manage_search),
                    label: Text('Búsqueda Libre'),
                  ),
                ],
                selected: {_mode},
                onSelectionChanged: (newSelection) {
                  setState(() => _mode = newSelection.first);
                },
              ),
              const SizedBox(height: 16),

              if (_mode == SearchMode.pico)
                _buildPicoForm(theme)
              else
                _buildLibreForm(theme),

              const SizedBox(height: 16),
              _buildFiltrosCard(theme),
              const SizedBox(height: 16),

              // Botones de Acción
              Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: searchState.isLoading ? null : _limpiarFormulario,
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Limpiar'),
                  ),
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: searchState.isLoading ? null : _ejecutarBusqueda,
                    icon: searchState.isLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.search),
                    label: Text(searchState.isLoading ? 'Buscando en PubMed...' : 'Buscar Evidencia'),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                    ),
                  ),
                ],
              ),
            ],
          );

          if (isWide) {
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 500,
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: searchContent,
                  ),
                ),
                const VerticalDivider(width: 1),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: _buildResultadosPanel(theme, searchState),
                  ),
                ),
              ],
            );
          } else {
            return SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  searchContent,
                  const SizedBox(height: 24),
                  const Divider(),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 700,
                    child: _buildResultadosPanel(theme, searchState),
                  ),
                ],
              ),
            );
          }
        },
      ),
    );
  }

  Widget _buildPicoForm(ThemeData theme) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(Icons.architecture, color: theme.colorScheme.primary, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Estructura PICO (Medicina Basada en Evidencia)',
                  style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Formulá tu duda clínica especificando cada componente para una búsqueda precisa.',
              style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
            ),
            const SizedBox(height: 12),

            // Chips con ejemplos rápidos
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                ActionChip(
                  avatar: const Icon(Icons.bolt, size: 14, color: Colors.amber),
                  label: const Text('Diabetes & SGLT2i', style: TextStyle(fontSize: 11)),
                  onPressed: () => _cargarEjemplo(
                    p: 'Adultos con diabetes tipo 2 y enfermedad cardiovascular',
                    i: 'Empagliflozina',
                    c: 'Placebo',
                    o: 'Mortalidad cardiovascular y hospitalizaciones por insuficiencia cardíaca',
                  ),
                ),
                ActionChip(
                  avatar: const Icon(Icons.bolt, size: 14, color: Colors.amber),
                  label: const Text('COVID-19 & Dexametasona', style: TextStyle(fontSize: 11)),
                  onPressed: () => _cargarEjemplo(
                    p: 'Pacientes hospitalizados con COVID-19 grave con soporte de oxígeno',
                    i: 'Dexametasona',
                    c: 'Cuidado habitual estándar',
                    o: 'Mortalidad a los 28 días',
                  ),
                ),
                ActionChip(
                  avatar: const Icon(Icons.bolt, size: 14, color: Colors.amber),
                  label: const Text('Fibrilación Auricular & DOACs', style: TextStyle(fontSize: 11)),
                  onPressed: () => _cargarEjemplo(
                    p: 'Adultos mayores con fibrilación auricular no valvular',
                    i: 'Anticoagulantes orales directos (DOACs)',
                    c: 'Warfarina',
                    o: 'Accidente cerebrovascular y hemorragia mayor',
                  ),
                ),
              ],
            ),
            const Divider(height: 24),

            // P: Paciente / Población
            _buildPicoField(
              letter: 'P',
              letterColor: Colors.blue.shade700,
              backgroundColor: Colors.blue.shade50,
              label: 'Población / Paciente / Problema *',
              helper: '¿Quién es el paciente o grupo de estudio?',
              hint: 'ej. Adultos con insuficiencia cardíaca con fracción de eyección reducida',
              controller: _poblacionController,
            ),
            const SizedBox(height: 12),

            // I: Intervención
            _buildPicoField(
              letter: 'I',
              letterColor: Colors.teal.shade700,
              backgroundColor: Colors.teal.shade50,
              label: 'Intervención / Tratamiento *',
              helper: '¿Qué fármaco, procedimiento o prueba diagnóstica se evalúa?',
              hint: 'ej. Dapagliflozina',
              controller: _intervencionController,
            ),
            const SizedBox(height: 12),

            // C: Comparación
            _buildPicoField(
              letter: 'C',
              letterColor: Colors.amber.shade900,
              backgroundColor: Colors.amber.shade50,
              label: 'Comparación / Control (Opcional)',
              helper: '¿Contra qué se compara? (ej. placebo, tratamiento habitual)',
              hint: 'ej. Placebo o tratamiento estándar',
              controller: _comparacionController,
            ),
            const SizedBox(height: 12),

            // O: Desenlace (Outcome)
            _buildPicoField(
              letter: 'O',
              letterColor: Colors.purple.shade700,
              backgroundColor: Colors.purple.shade50,
              label: 'Desenlace Clínico (Outcome) *',
              helper: '¿Qué resultado se busca medir? (ej. mortalidad, remisión, eventos)',
              hint: 'ej. Reducción de mortalidad por todas las causas y hospitalizaciones',
              controller: _outcomeController,
            ),

            if (_preguntaClinicaGenerada.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: theme.colorScheme.outlineVariant),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.help_outline, size: 16, color: theme.colorScheme.primary),
                        const SizedBox(width: 6),
                        Text(
                          'Pregunta clínica formulada:',
                          style: theme.textTheme.labelMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _preguntaClinicaGenerada,
                      style: theme.textTheme.bodyMedium?.copyWith(fontStyle: FontStyle.italic),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPicoField({
    required String letter,
    required Color letterColor,
    required Color backgroundColor,
    required String label,
    required String helper,
    required String hint,
    required TextEditingController controller,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 24,
              height: 24,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: backgroundColor,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: letterColor.withValues(alpha: 0.4)),
              ),
              child: Text(
                letter,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  color: letterColor,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                label,
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        TextField(
          controller: controller,
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(fontSize: 12, color: Colors.grey.shade400),
            isDense: true,
            border: const OutlineInputBorder(),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            helperText: helper,
            helperStyle: TextStyle(fontSize: 11, color: Colors.grey.shade600),
          ),
          style: const TextStyle(fontSize: 13),
        ),
      ],
    );
  }

  Widget _buildLibreForm(ThemeData theme) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Búsqueda Directa en PubMed',
              style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Text(
              'Ingresá términos libres o booleanos (AND, OR, NOT) tal como en PubMed.',
              style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _queryController,
              decoration: const InputDecoration(
                labelText: 'Términos de búsqueda en PubMed *',
                hintText: 'ej. empagliflozin AND "heart failure" AND mortality',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _ejecutarBusqueda(),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _preguntaLibreController,
              decoration: const InputDecoration(
                labelText: 'Pregunta clínica para la síntesis IA (opcional)',
                hintText: 'ej. ¿Cuál es el beneficio de la empagliflozina en insuficiencia cardíaca?',
                prefixIcon: Icon(Icons.help_outline),
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFiltrosCard(ThemeData theme) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(Icons.tune, color: theme.colorScheme.secondary, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Filtros Metodológicos & Parámetros',
                  style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Tipo de Estudio (MBE)
            DropdownButtonFormField<String>(
              initialValue: _filtroEstudio,
              decoration: const InputDecoration(
                labelText: 'Tipo de diseño de estudio (Filtro MBE)',
                isDense: true,
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(
                  value: 'all',
                  child: Text('Todos los estudios'),
                ),
                DropdownMenuItem(
                  value: 'rct',
                  child: Text('🏆 Ensayos Clínicos Controlados (RCT)'),
                ),
                DropdownMenuItem(
                  value: 'systematic_review',
                  child: Text('📚 Revisiones Sistemáticas / Meta-análisis'),
                ),
              ],
              onChanged: (val) {
                if (val != null) setState(() => _filtroEstudio = val);
              },
            ),
            const SizedBox(height: 12),

            // Filtro de Fecha
            DropdownButtonFormField<String>(
              initialValue: _filtroFecha,
              decoration: const InputDecoration(
                labelText: 'Rango de publicación',
                isDense: true,
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'all', child: Text('Cualquier fecha')),
                DropdownMenuItem(value: '5_years', child: Text('Últimos 5 años')),
                DropdownMenuItem(value: '10_years', child: Text('Últimos 10 años')),
              ],
              onChanged: (val) {
                if (val != null) setState(() => _filtroFecha = val);
              },
            ),
            const SizedBox(height: 12),

            // Cantidad de Resultados
            Row(
              children: [
                Text('Límite de artículos:', style: theme.textTheme.bodySmall),
                Expanded(
                  child: Slider(
                    value: _maxResults.toDouble(),
                    min: 5,
                    max: 50,
                    divisions: 9,
                    label: _maxResults.toString(),
                    onChanged: (v) => setState(() => _maxResults = v.round()),
                  ),
                ),
                Text('$_maxResults', style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),

            if (_mode == SearchMode.pico) ...[
              const Divider(height: 16),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                dense: true,
                title: const Text('Vocabulario controlado DeCS / MeSH'),
                subtitle: const Text(
                  'Resuelve P, I, C y O contra descriptores oficiales y repara la query ([MeSH Terms])',
                  style: TextStyle(fontSize: 11),
                ),
                value: _usarVocabulario,
                onChanged: (v) => setState(() => _usarVocabulario = v),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                dense: true,
                title: const Text('Priorizar calidad de la evidencia'),
                subtitle: const Text(
                  'Jerarquía: ETS/HTA > Revisiones sistemáticas y metaanálisis > ECA > cohortes y casos y controles',
                  style: TextStyle(fontSize: 11),
                ),
                value: _priorizarCalidad,
                onChanged: (v) => setState(() => _priorizarCalidad = v),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                dense: true,
                title: const Text('Optimizar con IA (Traducción a MeSH/Inglés)'),
                subtitle: const Text(
                  'Usa Gemini para convertir PICO en una query booleana médica de alta precisión',
                  style: TextStyle(fontSize: 11),
                ),
                value: _optimizarConIa,
                onChanged: (v) => setState(() => _optimizarConIa = v),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResultadosPanel(ThemeData theme, SearchState searchState) {
    if (searchState.isLoading) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 20),
            Text(
              _mode == SearchMode.pico && _optimizarConIa
                  ? 'Traduciendo términos PICO y consultando PubMed...'
                  : 'Recuperando evidencia científica desde PubMed...',
              style: theme.textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'Consultando NCBI E-utilities...',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
            ),
          ],
        ),
      );
    }

    if (searchState.error != null) {
      return Center(
        child: Card(
          color: theme.colorScheme.errorContainer,
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
                const SizedBox(height: 12),
                Text(
                  'Error en la búsqueda',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.onErrorContainer,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  searchState.error!,
                  textAlign: TextAlign.center,
                  style: TextStyle(color: theme.colorScheme.onErrorContainer),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (searchState.result == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.biotech, size: 72, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            Text(
              'Formulá tu pregunta PICO para recuperar evidencia',
              style: theme.textTheme.titleMedium?.copyWith(color: Colors.grey.shade700),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: 420,
              child: Text(
                'EvidencIA traducirá y estructurará tu consulta clínica para buscar ensayos clínicos y revisiones sistemáticas en PubMed.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade500, fontSize: 13),
              ),
            ),
          ],
        ),
      );
    }

    final result = searchState.result!;
    final articulos = result.articulos;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Barra de Información del Resultado
        Card(
          elevation: 0,
          color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: theme.colorScheme.outlineVariant),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Icon(Icons.check_circle_outline, color: theme.colorScheme.primary, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${articulos.length} artículos recuperados (de ${result.totalEncontrados} en PubMed)',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                    if (result.usadoIa)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.purple.shade50,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.purple.shade200),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.auto_awesome, size: 12, color: Colors.purple.shade700),
                            const SizedBox(width: 4),
                            Text(
                              'Optimizado con IA',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: Colors.purple.shade700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(width: 12),
                    TextButton.icon(
                      icon: Icon(
                        searchState.selectedPmids.length == articulos.length
                            ? Icons.deselect
                            : Icons.select_all,
                        size: 16,
                      ),
                      label: Text(
                        searchState.selectedPmids.length == articulos.length
                            ? 'Deseleccionar todos'
                            : 'Seleccionar todos (${articulos.length})',
                      ),
                      onPressed: () {
                        if (searchState.selectedPmids.length == articulos.length) {
                          ref.read(searchProvider.notifier).deseleccionarTodos();
                        } else {
                          ref.read(searchProvider.notifier).seleccionarTodos();
                        }
                      },
                    ),
                  ],
                ),
                if (result.avisoIa != null && !result.usadoIa) ...[
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.orange.shade300),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.warning_amber_rounded,
                            size: 16, color: Colors.orange.shade800),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            result.avisoIa!,
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.orange.shade900,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                if (result.preguntaClinica != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Pregunta: ${result.preguntaClinica}',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade700, fontStyle: FontStyle.italic),
                  ),
                ],
                const SizedBox(height: 6),
                InkWell(
                  onTap: () => setState(() => _mostrarQueryDetalle = !_mostrarQueryDetalle),
                  child: Row(
                    children: [
                      Icon(
                        _mostrarQueryDetalle ? Icons.arrow_drop_down : Icons.arrow_right,
                        size: 18,
                        color: Colors.grey.shade600,
                      ),
                      Text(
                        _mostrarQueryDetalle ? 'Ocultar query PubMed' : 'Ver query PubMed enviada',
                        style: TextStyle(fontSize: 11, color: theme.colorScheme.primary),
                      ),
                    ],
                  ),
                ),
                if (_mostrarQueryDetalle)
                  Container(
                    margin: const EdgeInsets.only(top: 8),
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.black87,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: SelectableText(
                      result.queryPubmed ?? result.query,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 11,
                        color: Colors.lightGreenAccent,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),

                VocabularioYJerarquiaPanel(result: result),
        const SizedBox(height: 8),

        if (articulos.isEmpty)
          Expanded(
            child: Center(
              child: Card(
                elevation: 0,
                color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                  side: BorderSide(color: theme.colorScheme.outlineVariant),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.search_off, size: 52, color: theme.colorScheme.primary),
                      const SizedBox(height: 12),
                      Text(
                        '0 artículos encontrados en PubMed',
                        style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        width: 440,
                        child: Text(
                          'PubMed indexa literatura médica en inglés. Si buscaste en español sin Gemini activo o con demasiados filtros estrictos combinados, PubMed puede no encontrar coincidencias exactas.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        alignment: WrapAlignment.center,
                        children: [
                          Chip(
                            avatar: Icon(Icons.tune, size: 14),
                            label: Text('Probar con "Todos los estudios"', style: TextStyle(fontSize: 11)),
                          ),
                          Chip(
                            avatar: Icon(Icons.translate, size: 14),
                            label: Text('Ingresar términos en inglés (ej. empagliflozin)', style: TextStyle(fontSize: 11)),
                          ),
                          Chip(
                            avatar: Icon(Icons.key, size: 14),
                            label: Text('Configurar GEMINI_API_KEY en backend/.env', style: TextStyle(fontSize: 11)),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          )
        else
          Expanded(
            child: ListView.builder(
              itemCount: articulos.length,
              itemBuilder: (context, index) {
                final article = articulos[index];
                return ArticleCard(
                  article: article,
                  isSelected: searchState.selectedPmids.contains(article.pmid),
                  onToggle: () => ref.read(searchProvider.notifier).toggleSeleccion(article.pmid),
                );
              },
            ),
          ),
      ],
    );
  }
}
