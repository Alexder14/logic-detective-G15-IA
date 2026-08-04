% =============================================================================
%  CASO 3 — <TITULO DEL CASO>
%  Responsable: <NOMBRE DEL INTEGRANTE>
% =============================================================================
%
%  ARCHIVO PENDIENTE. Aquí van SOLO HECHOS y las reglas propias de este caso.
%  Las reglas de inferencia compartidas ya están resueltas en reglas_base.pl y
%  este archivo las hereda con `:- include`. NO copies reglas_base.pl aquí y NO
%  la edites: si necesitas un predicado que no existe, habla con el coordinador.
%
%  ---------------------------------------------------------------------------
%  MÍNIMOS QUE EXIGE EL ENUNCIADO PARA ESTE CASO
%  ---------------------------------------------------------------------------
%
%    [ ]  4 sospechosos      -> sospechoso/1
%    [ ] 10 evidencias       -> evidencia/5  (+ evidencia_incrimina/2)
%    [ ]  5 lugares          -> lugar/2
%    [ ]  5 declaraciones    -> declaracion/3
%    [ ] 10 reglas de inferencia propias del caso (sección al final)
%
%  Además, para que el motor pueda concluir algo, este caso NECESITA:
%
%    [ ] caso/4                    identidad del caso (ya está abajo)
%    [ ] victima/1                 quién sufrió el incidente
%    [ ] escena_del_incidente/1    dónde ocurrió
%    [ ] hora_del_incidente/1      entero 0..23
%    [ ] medio_requerido/1         qué exigió el incidente (al menos uno)
%    [ ] coartada/4                una por sospechoso, con o sin respaldo
%    [ ] relacion/3                relaciones entre los involucrados
%
%  ---------------------------------------------------------------------------
%  ESQUEMA DE HECHOS
%  ---------------------------------------------------------------------------
%  El contrato completo, con los tipos y valores permitidos de cada argumento,
%  está en el encabezado de `reglas_base.pl`. Respétalo al pie de la letra: las
%  reglas base detectan las contradicciones por unificación sobre esos términos,
%  así que un functor mal escrito hace que el caso simplemente no concluya nada.
%
%  Los términos permitidos dentro de declaracion/3 son:
%      estuvo_en(Persona, Lugar, Hora)      no_estuvo_en(Persona, Lugar, Hora)
%      vio_a(Persona, Lugar, Hora)          conoce_a(P1, P2)
%      no_conoce_a(P1, P2)                  posee(Persona, Medio)
%
%  ---------------------------------------------------------------------------
%  DISEÑA EL CASO ANTES DE ESCRIBIRLO
%  ---------------------------------------------------------------------------
%  Un caso está bien construido si el motor llega a UN solo responsable y ese
%  responsable es el que tú querías. Para eso el culpable debe acumular
%  oportunidad + motivo + medios + coartada inválida + al menos 2 evidencias, y
%  los otros tres sospechosos deben quedar por debajo. Los distractores se
%  construyen dándoles una o dos de esas cosas, nunca todas.
%
%  Ver `caso_demo.pl` como ejemplo mínimo de formato (NO como ejemplo de
%  tamaño: ese caso no cumple los mínimos).
%
%  ---------------------------------------------------------------------------
%  CÓMO PROBAR TU CASO
%  ---------------------------------------------------------------------------
%      swipl prolog/caso3.pl
%      ?- caso3:resumen_caso(R).                  % verifica los conteos mínimos
%      ?- caso3:ranking_sospecha(R).              % revisa que el orden sea el que buscas
%      ?- caso3:responsable(P).                   % debe dar UNA sola respuesta
%      ?- caso3:contradicciones(C).
%      ?- caso3:explicacion(P, E), forall(member(R,E), (print(R), nl)).
%
%  Y desde el navegador, con el sistema levantado:
%      http://localhost:8080/investigacion/caso3
%
% =============================================================================

:- module(caso3, []).

:- include('reglas_base.pl').


% --- Identidad --------------------------------------------------------------
%  Actualiza el título, la descripción y la dificultad (facil|media|dificil).
%  La descripción es el texto que el usuario lee al abrir el caso.
caso(caso3,
     'Caso 3 (pendiente)',
     'Sin redactar. El responsable de este caso debe llenar prolog/caso3.pl.',
     media).


% --- Personas ---------------------------------------------------------------
%  sospechoso/1, testigo/1, victima/1, relacion/3


% --- Lugares y tiempo -------------------------------------------------------
%  lugar/2, escena_del_incidente/1, hora_del_incidente/1, lugar_conectado/2


% --- Acceso -----------------------------------------------------------------
%  tiene_llave/2, autorizado_en/2, registro_acceso/3


% --- Presencia --------------------------------------------------------------
%  visto_en/3


% --- Motivo -----------------------------------------------------------------
%  motivo/2


% --- Medios -----------------------------------------------------------------
%  medio_requerido/1, posee_medio/2


% --- Evidencias -------------------------------------------------------------
%  evidencia/5, evidencia_incrimina/2


% --- Declaraciones ----------------------------------------------------------
%  declaracion/3


% --- Coartadas --------------------------------------------------------------
%  coartada/4


% =============================================================================
%  REGLAS DE INFERENCIA PROPIAS DEL CASO 3  (mínimo 10)
% =============================================================================
%  Aquí van las reglas que solo tienen sentido en este caso y que no cabían en
%  reglas_base.pl. Constrúyelas SOBRE los predicados base, no en paralelo a
%  ellos. Ideas de reglas que suman a la rúbrica (usa listas, recursividad,
%  negación y algún corte):
%
%    - un rol específico del caso (turno_nocturno/1, tiene_acceso_al_sistema/1)
%    - una regla que combine dos evidencias del caso para una conclusión nueva
%    - una regla recursiva sobre relacion/3 (quién encubre a quién, en cadena)
%    - una regla con \+ que descarte a un sospechoso por una razón del caso
%    - una regla con findall/length que exija un mínimo de evidencias
%
%  Documenta cada regla con un comentario de una línea: la rúbrica califica que
%  el uso de listas, recursividad, unificación, negación y cortes sea
%  comprobable.
