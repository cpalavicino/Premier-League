# Optimización del calendario de la Premier League minimizando breaks de localía

## Enfoque

Investigación científica y optimización combinatoria mediante Programación Entera Mixta (MIP), implementada en Python con Gurobi.

## Descripción del problema

Este proyecto estudia la planificación del calendario de la **Premier League** como un torneo Round-Robin doble. La competición cuenta con 20 clubes: cada par de equipos se enfrenta dos veces durante la temporada, una en el estadio de cada club. Por ello, el calendario comprende 38 jornadas, con 10 partidos por jornada y un partido por equipo en cada jornada.

Se busca construir un calendario que asigne a cada encuentro una jornada y determine cuál equipo juega como local. El criterio principal es minimizar los **breaks**: situaciones en las que un club disputa dos jornadas consecutivas jugando ambos partidos como local o ambos como visitante. Reducirlos favorece una alternancia más equilibrada de localías y visitas a lo largo de la temporada.

La versión inicial se concentra en el calendario deportivo y no en fechas específicas. Restricciones operativas propias de la competición —por ejemplo, disponibilidad de estadios, seguridad, transmisiones televisivas y participación en torneos europeos— podrán incorporarse como extensiones si se cuenta con los datos necesarios.

## Datos y fuentes

Para construir y validar el conjunto de equipos, así como analizar calendarios históricos, se utilizarán archivos CSV de la Premier League publicados por [Football-Data.co.uk](https://www.football-data.co.uk/englandm.php). Los archivos incluyen resultados y datos de partidos; para este proyecto se extraen la fecha, el equipo local y el equipo visitante.

| Temporada | Archivo de datos |
|---|---|
| 2021-2022 | [CSV](https://www.football-data.co.uk/mmz4281/2122/E0.csv) |
| 2022-2023 | [CSV](https://www.football-data.co.uk/mmz4281/2223/E0.csv) |
| 2023-2024 | [CSV](https://www.football-data.co.uk/mmz4281/2324/E0.csv) |
| 2024-2025 | [CSV](https://www.football-data.co.uk/mmz4281/2425/E0.csv) |
| 2025-2026 | [CSV](https://www.football-data.co.uk/mmz4281/2526/E0.csv) |
| 2026-2027 | [CSV](https://www.football-data.co.uk/mmz4281/2627/E0.csv) |



**Uso y limitaciones:** los notebooks de `INSTANCIAS_PRUEBA` leen cada CSV directamente desde su URL. El modelo usa los equipos de la temporada para construir un calendario nuevo; los CSV no aportan una correspondencia fiable entre partidos y jornadas oficiales, por lo que no se usan para fijar el calendario optimizado ni para calcular breaks históricos. Las listas de clásicos, estadios compartidos, equipos europeos y jornadas críticas deben completarse con datos adicionales si se quieren activar esas restricciones. Se necesita conexión a Internet y una licencia válida de Gurobi para resolver el modelo.


## Objetivo del proyecto

Desarrollar y resolver con Gurobi un modelo MIP que genere calendarios factibles para la Premier League y minimice el total de breaks. Se analizará el calendario resultante, su distribución de localías y el desempeño del modelo en términos de tiempo de solución y calidad de la solución.

### Pregunta de investigación

¿Cómo puede formularse y resolverse un modelo de optimización para construir el calendario de una temporada de la Premier League que respete el formato de doble Round-Robin y minimice los partidos consecutivos de local o de visita?

## Inspiración científica

La formulación toma como inspiración el trabajo de **Fujii y Matsui (2025)** sobre modelos de programación lineal entera para minimizar breaks en calendarios deportivos Round-Robin. Este proyecto adapta ese enfoque a las características de la Premier League, en particular su formato de doble Round-Robin de 20 equipos y 38 jornadas.

> Completar la referencia bibliográfica de Fujii y Matsui (2025) con los datos de publicación utilizados en la investigación.