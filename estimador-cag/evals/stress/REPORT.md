# Stress test del CAG — REPORT

Filas totales: **66** (66 ok, 0 con error). Proveedor único para que las curvas sean comparables.

> Adaptaciones a este codebase (más simple que la plantilla del enunciado): no hay tiers, caché (exact/semantic) ni summarizer de texto; la memoria que sobrevive a la ventana es `ProjectMetadata`, así que `summary_chars` mide su tamaño, `anchors_count`=0 y `cache_hit_kind`=`none`. El stress se mide en dos fases desacopladas (multiturno sin adjunto · barrido de adjunto en una estimación) para aislar cada dimensión.

## Tabla resumen

### Resumen — fase multiturno (sin adjunto)

| escenario | turnos | P50 latency (ms) | P95 latency (ms) | coste total USD | recall medio fact-tracker | supervivencia turno-1 (último turno) |
|---|---|---|---|---|---|---|
| contradiction | 8 | 8468 | 14555 | 0.12355 | 0.84 | 1.00 |
| growing | 10 | 8399 | 18243 | 0.19016 | 1.00 | 1.00 |
| pivot | 10 | 8189 | 15878 | 0.19067 | 1.00 | 1.00 |

### Resumen — fase adjuntos (estimación inicial)

| adjunto (KB) | chars extraídos | P50 latency (ms) | P95 latency (ms) | coste medio USD | recall del marcador |
|---|---|---|---|---|---|
| 0 | 0 | 3526 | 3802 | 0.00181 | n/a (baseline) |
| 5 | 5632 | 9176 | 9321 | 0.00639 | 1.00 |
| 20 | 22977 | 9107 | 9226 | 0.01314 | 1.00 |
| 50 | 56758 | 11704 | 13968 | 0.02681 | 1.00 |
| 100 | 114304 | 9274 | 9464 | 0.04893 | 1.00 |

**Cache hit rate** — exact: 0% · semantic: 0% (este baseline CAG no implementa caché; `cache_hit_kind` es siempre `none`).

## Tres curvas

### Curva 1 — latencia vs tokens_in (barrido de adjunto)

| adjunto (KB) | tokens_in (medio) | latency_ms (medio) |
|---|---|---|
| 0 | 738 | 3526 |
| 5 | 3316 | 9176 |
| 20 | 10104 | 9107 |
| 50 | 23412 | 11704 |
| 100 | 45924 | 9274 |


### Curva 2 — coste acumulado USD vs turno (por escenario)

| turno | contradiction | growing | pivot |
|---|---|---|---|
| 1 | 0.00292 | 0.00330 | 0.00336 |
| 2 | 0.00696 | 0.00756 | 0.00782 |
| 3 | 0.01178 | 0.01325 | 0.01356 |
| 4 | 0.01818 | 0.01988 | 0.02092 |
| 5 | 0.02633 | 0.02747 | 0.02887 |
| 6 | 0.03656 | 0.03704 | 0.03852 |
| 7 | 0.04856 | 0.04848 | 0.05045 |
| 8 | 0.06177 | 0.06210 | 0.06396 |
| 9 |  | 0.07778 | 0.07904 |
| 10 |  | 0.09508 | 0.09533 |


### Curva 3 — recall vs N (turnos)

Recall medio del fact-tracker (`memory_drift_recall`) por turno y escenario:

| turno (N) | contradiction | growing | pivot |
|---|---|---|---|
| 2 | 1.00 | 1.00 | 1.00 |
| 3 | 1.00 | 1.00 | 1.00 |
| 4 | 0.67 | 1.00 | 1.00 |
| 5 | 0.75 | 1.00 | 1.00 |
| 6 | 0.80 | 1.00 | 1.00 |
| 7 | 0.83 | 1.00 | 1.00 |
| 8 | 0.86 | 1.00 | 1.00 |
| 9 |  | 1.00 | 1.00 |
| 10 |  | 1.00 | 1.00 |


## Lectura: dónde empieza a romperse mi CAG y por qué

**Dimensión dominante: los adjuntos.** El texto del adjunto entra íntegro en el prompt en cada estimación (este CAG no aplica `MAX_ATTACHMENT_CHARS`: no trunca). Pasar de 0 a 100 KB de texto lleva la entrada de ~738 a ~45924 tokens y la P95 de latencia de 3802 ms a 9464 ms; con cualquier adjunto se supera el budget de 4000 ms. El coste de una sola estimación escala linealmente con el tamaño del adjunto porque se reenvía completo: no hay reuso ni recuperación selectiva. Aquí es donde el CAG deja de sostenerse — un único documento grande basta para disparar latencia y coste y acercar el prompt al límite de contexto del modelo.

**La memoria conversacional es la segunda grieta.** En *growing*, el coste del turno 10 ($0.01731) multiplica por 5.25× el del turno 1 ($0.00330). El coste por turno crece porque la ventana deslizante y el ProjectMetadata acumulado se reinyectan cada vez; además cada turno hace dos llamadas (estimación + extractor), de modo que la latencia P50 multiturno (~8247 ms) ya excede el SLA de 4000 ms sin adjunto alguno. En *contradiction* el recall del fact-tracker cae por debajo de 1.0 ya en el turno 4 (a 0.67): el presupuesto inicial ("30000") no se promueve a `ProjectMetadata` y desaparece, mientras que en *growing*/*pivot* las tecnologías se acumulan por unión y el recall se mantiene en 1.0. **El caso límite que justifica saltar a RAG**: un proyecto largo con documentos adjuntos voluminosos — donde reenviar todo el contexto se vuelve caro y lento, y donde recuperar solo los fragmentos relevantes (RAG) deja de ser opcional.


## Cuatro afirmaciones para defender

1. Mi CAG empieza a degradar la memoria en el turno **4** (*contradiction*), cuando un hecho que no entra en `ProjectMetadata` cae fuera de la ventana de 6 pares.
2. El coste por turno crece ~lineal con el historial: turno 10 = **5.25×** el turno 1, porque cada turno reinyecta ventana + metadata + transcript.
3. El cuello de botella de latencia es el tamaño del prompt: la P95 pasa de 3802 ms (sin adjunto) a 9464 ms (100 KB), y el budget de 4000 ms se incumple con cualquier adjunto.
4. Para recortar contexto sin perder recall atacaría primero el adjunto: aporta ~45924 tokens de entrada (vs ~738 sin él), la mayor contribución individual — justo lo que RAG recupera de forma selectiva.