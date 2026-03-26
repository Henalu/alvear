# Project Brief

## Qué es Alvear

Alvear es un `swarm intelligence engine` para ensayar reacciones colectivas antes de ejecutar una decisión real. No se posiciona como oráculo ni como sistema de predicción infalible. Su valor está en simular cómo podrían reaccionar actores distintos cuando un producto, una campaña o una decisión entra en el mundo.

## Idea fundacional

La inteligencia útil no está en un agente aislado, sino en la dinámica del sistema. Igual que en un alvear real, lo importante es el comportamiento emergente de muchas piezas interactuando.

## Propósito

Reducir decisiones importantes tomadas a ciegas. Alvear existe para que equipos, marcas y organizaciones puedan preguntar “¿qué pasaría si hacemos esto?” antes de pagar el coste de averiguarlo en producción.

## Visión

Un mundo donde las decisiones importantes se ensayan antes de ejecutarse.

## Misión actual

Convertir materiales de contexto en:

1. Una ontología útil para simulación social.
2. Un grafo local de actores, relaciones y contexto.
3. Un conjunto de perfiles de agentes para OASIS.
4. Una simulación social ejecutable.
5. Un resumen accionable con patrones y fricciones.

## Qué vendemos realmente

No vendemos certeza.
Vendemos claridad bajo incertidumbre.

## Usuario inicial

La primera cuña de entrada es para:

- fundadores y equipos pequeños
- marketers estratégicos
- creadores de producto
- perfiles tech curiosos

Todos comparten una necesidad: quieren validar reacciones antes de lanzar, pero no tienen recursos para research profundo continuo ni quieren depender solo de intuición.

## Caso de uso v1

Escenario canónico: lanzamiento de producto en español.

Preguntas que debe ayudar a responder:

- qué narrativas aparecen primero
- qué objeciones dominan
- qué actores amplifican o frenan la conversación
- qué señales de credibilidad o desconfianza emergen

## Valores de producto

- Honestidad radical sobre la incertidumbre.
- Utilidad por encima de impresionar.
- Acceso por encima de exclusividad.
- Curiosidad sin ego.
- Optimismo práctico.

## Tono de marca

Alvear debe sonar:

- claro
- directo
- cálido
- sin tecnicismo innecesario
- humilde sobre las limitaciones
- concreto y útil

Debe evitar sonar:

- corporativo
- mesiánico
- excesivamente formal
- opaco
- grandilocuente

## Restricciones de fase

- V1 es `backend + CLI`.
- La UI no es prioridad inmediata.
- Todo debe poder correr sin Zep Cloud.
- El stack objetivo es `Neo4j local + Ollama`.
- La simulación inicial debe mantenerse contenida: hasta 24 agentes y 12 rondas por defecto.

## Métrica de progreso en esta fase

La pregunta no es si “parece IA avanzada”.
La pregunta es si un usuario puede:

1. cargar materiales
2. construir un grafo útil
3. preparar una simulación
4. ejecutarla localmente
5. obtener un resumen mínimamente accionable
