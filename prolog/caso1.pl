% =============================================================================
%  CASO 1 — EL COLLAR ESTELAR
%  Responsable: Madeline Prado (carné 202100039)
% =============================================================================
%
%  Gala benéfica anual de la Fundación Belmonte. El collar de diamantes
%  "Estelar", exhibido en una vitrina de seguridad del salón principal,
%  desaparece entre las 21:55 y las 22:30. Alguien desactivó la alarma
%  manualmente justo en la ventana de una ronda de vigilancia.
%
%  Cómo probar:
%      swipl prolog/caso1.pl
%      ?- caso1:resumen_caso(R).
%      ?- caso1:ranking_sospecha(R).
%      ?- caso1:responsable(P).
%      ?- caso1:contradicciones(C).
%      ?- caso1:explicacion(P, E), forall(member(R,E), (print(R), nl)).
%      ?- caso1:ladron_del_collar(P).           % conclusión propia del caso
%
% =============================================================================

:- module(caso1, []).

:- include('reglas_base.pl').


% --- Identidad ----------------------------------------------------------
caso(caso1,
     'El Collar Estelar',
     'Durante la gala benéfica de la Fundación Belmonte, el collar de diamantes "Estelar" desaparece de su vitrina de seguridad en el salón principal, entre las 21:55 y las 22:30.',
     media).


% --- Personas -------------------------------------------------------------
sospechoso(victor_cordero).   % jefe de seguridad contratado para el evento
sospechoso(isabela_duarte).   % prima de Adriana, coheredera de la fundación
sospechoso(valeria_montes).   % rival, dueña de una joyería competidora
sospechoso(hugo_paredes).     % organizador del evento y jefe de catering

testigo(bruno_salcedo).       % mesero / apoyo de seguridad esa noche
testigo(camila_rios).         % asistente de organización del evento
testigo(teodoro_vidal).       % socio de Valeria Montes

victima(adriana_belmonte).    % anfitriona de la gala, dueña del collar

relacion(victor_cordero, adriana_belmonte, empleado).
relacion(isabela_duarte, adriana_belmonte, heredero).
relacion(valeria_montes, adriana_belmonte, rival).
relacion(hugo_paredes,   adriana_belmonte, empleado).
relacion(hugo_paredes,   victor_cordero,   socio).   % Hugo contrató a la empresa de Víctor


% --- Lugares y tiempo -----------------------------------------------------
lugar(salon_principal,      'Salón principal de la gala, con la vitrina de seguridad del collar').
lugar(guardarropa,          'Guardarropa junto al salón principal').
lugar(cocina_catering,      'Cocina y área de catering').
lugar(oficina_organizacion, 'Oficina de organización del evento').
lugar(estacionamiento,      'Estacionamiento y entrada de servicio').

escena_del_incidente(salon_principal).
hora_del_incidente(22).

lugar_conectado(salon_principal, guardarropa).
lugar_conectado(salon_principal, cocina_catering).
lugar_conectado(cocina_catering, estacionamiento).
lugar_conectado(guardarropa,     oficina_organizacion).


% --- Acceso -----------------------------------------------------------------
tiene_llave(victor_cordero, salon_principal).      % llave del gabinete de seguridad
autorizado_en(hugo_paredes, salon_principal).       % acceso legítimo como organizador


% --- Presencia --------------------------------------------------------------
visto_en(victor_cordero, salon_principal, 22).      % en la escena, hora del robo
visto_en(victor_cordero, guardarropa,     21).      % ronda de las 21h
visto_en(victor_cordero, cocina_catering, 20).      % ronda de las 20h


% --- Motivo -----------------------------------------------------------------
motivo(victor_cordero, deuda).                      % deudas de juego


% --- Medios -----------------------------------------------------------------
medio_requerido(codigo_alarma).
medio_requerido(llave).

posee_medio(victor_cordero, codigo_alarma).         % la configuró esa misma noche
posee_medio(victor_cordero, llave).                 % llave del gabinete de seguridad
posee_medio(hugo_paredes,   llave).                 % llaves maestras del evento


% --- Evidencias ---------------------------------------------------------------
evidencia(e1,  huella,     salon_principal,      22,          'Huella parcial en el marco de la vitrina de seguridad, coincide con las de Víctor Cordero').
evidencia(e2,  video,      guardarropa,          22,          'Cámara de respaldo del guardarropa capta a Víctor pasando con un maletín poco antes del cierre').
evidencia(e3,  registro,   salon_principal,      21,          'Registro del sistema: la alarma fue desactivada manualmente con el código de Víctor a las 21:55').
evidencia(e4,  objeto,     estacionamiento,      desconocida, 'Estuche vacío del collar hallado en un vehículo de servicio').
evidencia(e5,  documento,  oficina_organizacion, desconocida, 'Reporte de la aseguradora confirmando la desaparición del collar').
evidencia(e6,  adn,        salon_principal,      desconocida, 'Rastro de ADN sin identificar en el cierre de la vitrina').
evidencia(e7,  testimonio, estacionamiento,      desconocida, 'Un valet recuerda a Valeria Montes hablando por teléfono sobre "la pieza" la noche anterior').
evidencia(e8,  documento,  oficina_organizacion, desconocida, 'Correo de Valeria Montes ofreciendo comprar el collar directamente a Adriana, rechazado').
evidencia(e9,  testimonio, cocina_catering,      desconocida, 'Un mesero comenta que Hugo estuvo yendo y viniendo por el salón revisando la decoración esa noche').
evidencia(e10, documento,  oficina_organizacion, desconocida, 'Copia del acuerdo societario donde Isabela Duarte figura como coheredera de la fundación y su colección').

evidencia_incrimina(e1, victor_cordero).
evidencia_incrimina(e2, victor_cordero).
evidencia_incrimina(e3, victor_cordero).
evidencia_incrimina(e7, valeria_montes).
evidencia_incrimina(e8, valeria_montes).
evidencia_incrimina(e9, hugo_paredes).
evidencia_incrimina(e10, isabela_duarte).
% e4, e5, e6 quedan sin evidencia_incrimina: son evidencia neutral de la escena.


% --- Declaraciones ------------------------------------------------------------
declaracion(d1, victor_cordero, no_estuvo_en(victor_cordero, salon_principal, 22)).
declaracion(d2, bruno_salcedo,  vio_a(victor_cordero, salon_principal, 22)).
declaracion(d3, isabela_duarte, estuvo_en(isabela_duarte, oficina_organizacion, 22)).
declaracion(d4, hugo_paredes,   estuvo_en(hugo_paredes, cocina_catering, 22)).
declaracion(d5, hugo_paredes,   posee(hugo_paredes, llave)).


% --- Coartadas ------------------------------------------------------------
coartada(victor_cordero, estacionamiento,      22, ninguno).                % sin respaldo
coartada(isabela_duarte, oficina_organizacion, 22, testigo(camila_rios)).   % válida
coartada(hugo_paredes,   cocina_catering,      22, testigo(camila_rios)).   % válida
coartada(valeria_montes, guardarropa,          22, testigo(teodoro_vidal)). % válida


% --- Hechos propios del caso ------------------------------------------------
%  area_de_ronda/1: los tres puntos que Víctor debía recorrer en su ronda de
%  vigilancia esa noche. Lo usa la regla 1.
area_de_ronda(salon_principal).
area_de_ronda(guardarropa).
area_de_ronda(cocina_catering).


% =============================================================================
%  REGLAS DE INFERENCIA PROPIAS DEL CASO 1  (10)
% =============================================================================
%  Construidas sobre los predicados de reglas_base.pl, no en paralelo a ellos.

%! cubrio_areas(+Persona, +Areas) is semidet.
%  Recursión sobre la lista de áreas: caso base, lista vacía se cumple sola;
%  caso recursivo, exige ver a Persona en la cabeza y sigue con el resto.
cubrio_areas(_, []).
cubrio_areas(Persona, [Area|Resto]) :-
    visto_en(Persona, Area, _),
    cubrio_areas(Persona, Resto).

%! 1. hizo_ronda_de_vigilancia(?Persona) is nondet.
%  REGLA 1 — listas + recursividad: arma con findall/3 la lista de áreas de
%  ronda y la recorre con cubrio_areas/2 para confirmar que Persona pasó por
%  las tres, como se espera del personal de seguridad.
hizo_ronda_de_vigilancia(Persona) :-
    findall(Area, area_de_ronda(Area), Areas),
    cubrio_areas(Persona, Areas).

%! 2. desactivo_la_alarma(?Persona) is nondet.
%  REGLA 2 — unificación: combina dos hechos del caso (que Persona tenga el
%  código de alarma como medio, y que exista evidencia tipo registro que la
%  incrimine) en una conclusión nueva que ninguno de los dos da por separado.
desactivo_la_alarma(Persona) :-
    tiene_medios(Persona, codigo_alarma),
    evidencia(IdEv, registro, _, _, _),
    evidencia_incrimina(IdEv, Persona).

%! cadena_de_confianza(+Origen, +Destino, -Cadena) is nondet.
%  Como ruta/3 en reglas_base.pl, pero sobre el grafo de relacion/3 en vez
%  del de lugares.
cadena_de_confianza(Origen, Destino, Cadena) :-
    cadena_de_confianza_(Origen, Destino, [Origen], Invertida),
    reverse(Invertida, Cadena).

cadena_de_confianza_(Destino, Destino, Visitados, Visitados).
cadena_de_confianza_(Actual, Destino, Visitados, Cadena) :-
    relacion_bidireccional(Actual, Siguiente, _),
    \+ victima(Siguiente),           % la cadena no rebota en la víctima
    \+ member(Siguiente, Visitados),
    cadena_de_confianza_(Siguiente, Destino, [Siguiente|Visitados], Cadena).

%! 3. pudo_pasar_la_joya(?Persona) is nondet.
%  REGLA 3 — recursividad + listas + negación: sigue la cadena de relaciones
%  de confianza desde el responsable para ver a qué otro sospechoso pudo
%  haberle entregado el collar; \+ member/2 evita ciclos en la recursión.
%  Persona se liga primero vía sospechoso/1: comparar con \== antes de ligar
%  la dejaría pasar de forma vacía y once/1 se quedaría con el caso base de
%  la cadena (el propio Ladron).
pudo_pasar_la_joya(Persona) :-
    responsable(Ladron),
    sospechoso(Persona),
    Persona \== Ladron,
    once(cadena_de_confianza(Ladron, Persona, _)).

%! areas_con_acceso(+Persona, -Lista) is det.
%  Lista sin repetidos de los lugares del caso a los que Persona tiene acceso.
areas_con_acceso(Persona, Lista) :-
    findall(Lugar, (lugar(Lugar, _), acceso_al_lugar(Persona, Lugar)), Sin),
    sort(Sin, Lista).

%! 4. acceso_privilegiado(?Persona) is nondet.
%  REGLA 4 — listas: cuenta con findall/length a cuántas de las cinco zonas
%  del evento tiene acceso Persona; tres o más cuenta como acceso privilegiado.
acceso_privilegiado(Persona) :-
    areas_con_acceso(Persona, Areas),
    length(Areas, N),
    N >= 3.

%! 5. coartada_totalmente_sola(?Persona) is nondet.
%  REGLA 5 — negación: la coartada de Persona no tiene respaldo Y nadie más
%  fue visto en ese mismo lugar a esa hora que pudiera corroborarla ni de
%  casualidad.
coartada_totalmente_sola(Persona) :-
    coartada(Persona, Lugar, Hora, ninguno),
    \+ ( visto_en(Otro, Lugar, HoraOtro),
         Otro \== Persona,
         horas_compatibles(Hora, HoraOtro)
       ).

%! 6. unico_con_medios_y_oportunidad(?Persona) is semidet.
%  REGLA 6 — negación + corte: confirma que Persona es la única sospechosa
%  que reúne oportunidad Y medios a la vez. El corte la deja semidet: ya se
%  probó que nadie más califica, no hace falta seguir buscando.
unico_con_medios_y_oportunidad(Persona) :-
    sospechoso(Persona),
    tuvo_oportunidad(Persona, _),
    tiene_medios(Persona, _),
    \+ ( sospechoso(Otro),
         Otro \== Persona,
         tuvo_oportunidad(Otro, _),
         tiene_medios(Otro, _)
       ),
    !.

%! 7. nivel_riesgo_joya(?Persona, -Nivel) is nondet.
%  REGLA 7 — cortes en cascada: clasifica a Persona por su combinación de
%  acceso privilegiado y evidencia directa, con un criterio propio de este
%  caso (igual estilo que clasificar_sospecha/2 en reglas_base.pl).
nivel_riesgo_joya(Persona, alto) :-
    acceso_privilegiado(Persona),
    evidencia_directa_contra(Persona, _),
    !.
nivel_riesgo_joya(Persona, medio) :-
    ( acceso_privilegiado(Persona) ; evidencia_directa_contra(Persona, _) ),
    !.
nivel_riesgo_joya(_, bajo).

%! contar_lista(+Lista, -N) is det.
%  Recursión manual para contar los elementos de una lista, sin usar
%  length/2 de la librería: caso base lista vacía, caso recursivo suma 1.
contar_lista([], 0).
contar_lista([_|Resto], N) :-
    contar_lista(Resto, M),
    N is M + 1.

%! evidencias_directas_contra(+Persona, -Lista) is det.
evidencias_directas_contra(Persona, Lista) :-
    findall(IdEv, evidencia_directa_contra(Persona, IdEv), Sin),
    sort(Sin, Lista).

%! 8. acusacion_formal_procede(?Persona) is nondet.
%  REGLA 8 — recursividad + listas: usa contar_lista/2 (recursión propia, no
%  length/2) sobre las evidencias directas para exigir al menos dos antes de
%  que una acusación formal proceda.
acusacion_formal_procede(Persona) :-
    evidencias_directas_contra(Persona, Lista),
    contar_lista(Lista, N),
    N >= 2.

%! 9. no_es_sospechoso_creible(?Persona) is nondet.
%  REGLA 9 — negación doble: descarta a quien tuvo acceso al salón pero no
%  tiene ni motivo ni evidencia directa en contra (protege a alguien como
%  Hugo, cuyo único "pecado" es haber podido entrar).
no_es_sospechoso_creible(Persona) :-
    sospechoso(Persona),
    \+ tiene_motivo(Persona, _),
    \+ evidencia_directa_contra(Persona, _),
    once(acceso_al_lugar(Persona, salon_principal)).

%! 10. ladron_del_collar(?Persona) is semidet.
%  REGLA 10 — unificación + listas + negación + corte: reúne las reglas
%  específicas del caso (desactivó la alarma, hizo la ronda, coartada sin
%  ningún respaldo, acusación formal procede) y con un findall/3 confirma
%  que nadie más las cumple todas a la vez. Conclusión propia del caso, en
%  paralelo a responsable/1 de reglas_base.pl pero con criterios propios.
ladron_del_collar(Persona) :-
    sospechoso(Persona),
    desactivo_la_alarma(Persona),
    hizo_ronda_de_vigilancia(Persona),
    coartada_totalmente_sola(Persona),
    acusacion_formal_procede(Persona),
    findall(Otro,
            ( sospechoso(Otro),
              Otro \== Persona,
              desactivo_la_alarma(Otro)
            ),
            OtrosSospechosos),
    OtrosSospechosos == [],
    !.
