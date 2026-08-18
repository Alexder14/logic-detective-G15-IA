% =============================================================================
%  CASO 2 — <TITULO DEL CASO>
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
%      swipl prolog/caso2.pl
%      ?- caso2:resumen_caso(R).                  % verifica los conteos mínimos
%      ?- caso2:ranking_sospecha(R).              % revisa que el orden sea el que buscas
%      ?- caso2:responsable(P).                   % debe dar UNA sola respuesta
%      ?- caso2:contradicciones(C).
%      ?- caso2:explicacion(P, E), forall(member(R,E), (print(R), nl)).
%
%  Y desde el navegador, con el sistema levantado:
%      http://localhost:8080/investigacion/caso2
%
% =============================================================================

%:- module(caso2, []).

% :- include('reglas_base.pl').


% --- Identidad --------------------------------------------------------------
%  Actualiza el título, la descripción y la dificultad (facil|media|dificil).
%  La descripción es el texto que el usuario lee al abrir el caso.
%caso(caso2,
%     'Caso 2 (pendiente)',
%     'Sin redactar. El responsable de este caso debe llenar prolog/caso2.pl.',
%     media).


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
%  REGLAS DE INFERENCIA PROPIAS DEL CASO 2  (mínimo 10)
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



% ========================================================================================================







% ========================================================================================================
%  CASO 2 — El Sabotaje en el Laboratorio de I+D (investigacion y desarrollo)

%   En empresas tecnológicas, farmacéuticas o industriales, el departamento de I+D es la división encargada de
%   crear nuevos productos, patentes, fórmulas o tecnologías antes de que salgan al mercado. Los laboratorios
%   de I+D suelen manejar secretos industriales de muy alto valor, por lo que son escenarios habituales para
%   historias de espionaje corporativo, robos o sabotajes.

%  Responsable: Henrry Martinez
% ========================================================================================================


:- module(caso2, []).

:- dynamic sospechoso/1, victima/1, testigo/1, relacion/3,
           lugar/2, escena_del_incidente/1, hora_del_incidente/1, lugar_conectado/2,
           tiene_llave/2, autorizado_en/2, registro_acceso/3,
           visto_en/3, motivo/2, medio_requerido/1, posee_medio/2,
           evidencia/5, evidencia_incrimina/2, declaracion/3, coartada/4, caso/4.

:- include('reglas_base.pl').


% --- Identidad --------------------------------------------------------------
caso(caso2,
     'El Sabotaje en el Laboratorio de I+D',
     'A las 22:00 horas se produjo la destrucción de los servidores principales y el robo de la fórmula del prototipo X-100 en la empresa BioTech. La víctima principal es el Dr. Aris, científico jefe. El culpable destruyó los respaldos y extrajo la fórmula utilizando conocimientos técnicos y llaves de acceso.',
     media).


% --- Personas ---------------------------------------------------------------
victima(dr_aris).

sospechoso(elena).
sospechoso(carlos).
sospechoso(roberto).
sospechoso(sofia).

testigo(marcos).

relacion(elena, dr_aris, jefe).
relacion(carlos, dr_aris, rival).
relacion(roberto, dr_aris, deudor).
relacion(sofia, dr_aris, empleado).
relacion(marcos, carlos, amigo).
relacion(elena, carlos, ex_pareja).


% --- Lugares y tiempo -------------------------------------------------------
escena_del_incidente(laboratorio_limpio).
hora_del_incidente(22).

lugar(laboratorio_limpio, 'Zona estéril donde se guarda la fórmula X-100').
lugar(sala_servidores, 'Habitación contigua con los servidores centrales').
lugar(oficina_central, 'Oficina administrativa principal').
lugar(biblioteca, 'Área de estudio y consulta de archivos').
lugar(caseta_guardia, 'Puesto de control de entrada y monitoreo de seguridad').

lugar_conectado(laboratorio_limpio, sala_servidores).
lugar_conectado(laboratorio_limpio, oficina_central).
lugar_conectado(oficina_central, biblioteca).
lugar_conectado(oficina_central, caseta_guardia).


% --- Acceso -----------------------------------------------------------------
tiene_llave(elena, laboratorio_limpio).
tiene_llave(carlos, sala_servidores).
tiene_llave(sofia, caseta_guardia).

autorizado_en(elena, laboratorio_limpio).
autorizado_en(dr_aris, laboratorio_limpio).
autorizado_en(sofia, caseta_guardia).

registro_acceso(carlos, sala_servidores, 22).
registro_acceso(roberto, oficina_central, 21).
registro_acceso(elena, biblioteca, 22).


% --- Presencia --------------------------------------------------------------
visto_en(carlos, laboratorio_limpio, 22).
visto_en(elena, biblioteca, 22).
visto_en(roberto, oficina_central, 21).
visto_en(sofia, caseta_guardia, 22).


% --- Motivo -----------------------------------------------------------------
motivo(carlos, venganza).
motivo(roberto, deuda).


% --- Medios -----------------------------------------------------------------
medio_requerido(conocimiento_tecnico).
medio_requerido(llave).

posee_medio(carlos, conocimiento_tecnico).
posee_medio(carlos, llave).
posee_medio(elena, llave).
posee_medio(roberto, fuerza).


% --- Evidencias -------------------------------------------------------------
% evidencia(IdEv, Tipo, Lugar, Hora, Descripcion)
evidencia(ev1, huella, laboratorio_limpio, 22, 'Huellas dactilares de Carlos en el terminal principal').
evidencia(ev2, video, laboratorio_limpio, 22, 'Grabación borrosa de figura masculina operando la consola').
evidencia(ev3, adn, laboratorio_limpio, 22, 'Cabello encontrado junto al servidor destruido').
evidencia(ev4, documento, oficina_central, 21, 'Pagaré firmado por Roberto con vencimiento esa misma noche').
evidencia(ev5, registro, sala_servidores, 22, 'Bitácora digital del sistema con login usando credenciales de Carlos').
evidencia(ev6, objeto, laboratorio_limpio, 22, 'Memoria USB con herramientas de hackeo olvidada en el escritorio').
evidencia(ev7, registro, biblioteca, 22, 'Registro de préstamo de libro firmado por Elena').
evidencia(ev8, video, caseta_guardia, 22, 'Cámara mostrando a Sofía dormida en la caseta').
evidencia(ev9, documento, laboratorio_limpio, 22, 'Impresión parcial del código fuente de la fórmula X-100').
evidencia(ev10, huella, sala_servidores, 22, 'Huella de calzado deportivo talla 42 coincidente con Carlos').

evidencia_incrimina(ev1, carlos).
evidencia_incrimina(ev2, carlos).
evidencia_incrimina(ev3, carlos).
evidencia_incrimina(ev4, roberto).
evidencia_incrimina(ev5, carlos).
evidencia_incrimina(ev6, carlos).
evidencia_incrimina(ev9, carlos).
evidencia_incrimina(ev10, carlos).


% --- Declaraciones ----------------------------------------------------------
% declaracion(IdDecl, Autor, Contenido)
declaracion(dec1, carlos, no_estuvo_en(carlos, laboratorio_limpio, 22)).
declaracion(dec2, elena, estuvo_en(elena, biblioteca, 22)).
declaracion(dec3, roberto, no_estuvo_en(roberto, laboratorio_limpio, 22)).
declaracion(dec4, sofia, no_estuvo_en(carlos, laboratorio_limpio, 22)).
declaracion(dec5, marcos, vio_a(carlos, biblioteca, 22)).
declaracion(dec6, carlos, no_conoce_a(carlos, dr_aris)).


% --- Coartadas --------------------------------------------------------------
% coartada(Persona, Lugar, Hora, Respaldo)
coartada(elena, biblioteca, 22, documento(ev7)).
coartada(carlos, biblioteca, 22, testigo(marcos)).
coartada(roberto, oficina_central, 21, ninguno).
coartada(sofia, caseta_guardia, 22, camara(caseta_guardia)).


% =============================================================================
%  REGLAS DE INFERENCIA PROPIAS DEL CASO 2 (10 Reglas requeridas)
% =============================================================================

%! R1: Red de encubrimiento sospechoso (Recursividad sobre relaciones)
%  Determina si una persona está vinculada socialmente con otra directamente o a través de intermediarios.
cadena_relaciones(A, B, [A, B]) :- 
    relacion(A, B, _).
cadena_relaciones(A, B, [A|Camino]) :- 
    relacion(A, C, _), 
    A \== C, 
    cadena_relaciones(C, B, Camino).

%! R2: Acceso técnico especializado (Unificación y Filtro)
%  Verifica si una persona posee conocimientos técnicos y acceso a la sala de servidores.
tiene_acceso_tecnico(Persona) :-
    posee_medio(Persona, conocimiento_tecnico),
    (tiene_llave(Persona, sala_servidores) ; registro_acceso(Persona, sala_servidores, _)).

%! R3: Descarte de sospechoso por coartada documental irrefutable (Negación \+)
%  Un sospechoso es descartado si su coartada está respaldada por un documento válido y no hay evidencia directa en su contra.
sospechoso_descartado_documental(Persona) :-
    sospechoso(Persona),
    coartada(Persona, _, _, documento(IdEv)),
    evidencia(IdEv, _, _, _, _),
    \+ evidencia_directa_contra(Persona, _).

%! R4: Testimonio de encubrimiento falso (Corte ! y Negación \+)
%  Un testigo respalda a un sospechoso pero la evidencia física demuestra que el sospechoso estuvo en la escena.
testigo_falso_encubridor(Testigo, Sospechoso) :-
    declaracion(_IdDecl, Testigo, vio_a(Sospechoso, _, Hora)),
    evidencia(IdEv, Tipo, Escena, HoraEv, _),
    escena_del_incidente(Escena),
    tipo_evidencia_directa(Tipo),
    evidencia_incrimina(IdEv, Sospechoso),
    horas_compatibles(Hora, HoraEv),
    !.

%! R5: Conteo masivo de evidencias físicas en contra (Listas + findall + length)
%  Verifica si una persona acumula un número crítico (>= 3) de evidencias físicas.
evidencias_criticas(Persona, Cantidad) :-
    sospechoso(Persona),
    findall(IdEv, evidencia_incrimina(IdEv, Persona), Lista),
    length(Lista, Cantidad),
    Cantidad >= 3.

%! R6: Violación de protocolo de seguridad (Acceso no autorizado a hora crítica)
%  Detecta si la persona accedió a un lugar sin estar formalmente autorizada en la hora del incidente.
violacion_protocolo(Persona, Lugar) :-
    registro_acceso(Persona, Lugar, Hora),
    hora_del_incidente(Hora),
    \+ autorizado_en(Persona, Lugar).

%! R7: Contradicción de testimonio contra móvil conocido (Unificación)
%  Niega conocer a la víctima pero existe una relación registrada de rivalidad o deuda.
miente_sobre_relacion(Persona) :-
    declaracion(_, Persona, no_conoce_a(Persona, Victima)),
    victima(Victima),
    relacion(Persona, Victima, _).

%! R8: Sospechoso de alto riesgo por perfil técnico e interés económico (Regla compuesta)
%  Combina motivo de venganza o deuda con posesión de medios técnicos.
perfil_alto_riesgo(Persona) :-
    sospechoso(Persona),
    motivo(Persona, Motivo),
    (Motivo == venganza ; Motivo == deuda),
    posee_medio(Persona, conocimiento_tecnico).

%! R9: Vulnerabilidad en la vigilancia de seguridad (Negación y Unificación)
%  Detecta si el personal de guardia falló en su deber durante la hora del incidente.
neglicencia_guardia(Guardia) :-
    autorizado_en(Guardia, caseta_guardia),
    evidencia(IdEv, video, caseta_guardia, Hora, _),
    hora_del_incidente(Hora),
    evidencia_incrimina(IdEv, Guardia).

%! R10: Confirmación de presencia por multiplicidad de medios (Recursividad/Iteración sobre lista de indicios)
%  Calcula si los medios combinados de la persona garantizan su capacidad de haber ejecutado el sabotaje.
capacidad_ejecucion_completa(Persona) :-
    medio_requerido(M1),
    medio_requerido(M2),
    M1 \== M2,
    posee_medio(Persona, M1),
    posee_medio(Persona, M2),
    !.
