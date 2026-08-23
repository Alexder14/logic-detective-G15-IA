% Reglas de inferencia que comparten los tres casos. Sin hechos: los hechos los
% aporta cada casoN.pl.
%
% Cada caso es un modulo que incluye este archivo, y asi trabaja las reglas
% sobre sus propios hechos:
%
%     :- module(caso1, []).
%     :- include('reglas_base.pl').
%     ... hechos del caso 1 ...
%
%     ?- caso1:sospechoso_principal(P).
%     ?- caso1:explicacion(P, E).
%
% Los predicados de hechos se declaran dinamicos mas abajo, asi que el archivo
% se puede consultar solo y las consultas fallan en vez de dar existence_error.
%
%
% ESQUEMA DE HECHOS QUE DEBE APORTAR CADA casoN.pl
% ------------------------------------------------
% Es el unico punto de acoplamiento del proyecto. Respeta nombres y aridades; si
% falta algo, avisa antes de inventar un predicado nuevo.
%
%   caso(Id, Titulo, Descripcion, Dificultad)   Dificultad: facil|media|dificil
%
%   sospechoso(Persona)      testigo(Persona)      victima(Persona)
%   relacion(Persona1, Persona2, Tipo)
%       Tipo: socio|hermano|ex_pareja|jefe|empleado|deudor|acreedor|rival|
%             heredero|vecino|amigo
%
%   lugar(Lugar, Descripcion)          escena_del_incidente(Lugar)
%   hora_del_incidente(Hora)           % entero 0..23
%   lugar_conectado(Lugar1, Lugar2)    % adyacencia fisica, un solo sentido
%
%   tiene_llave(Persona, Lugar)        autorizado_en(Persona, Lugar)
%   registro_acceso(Persona, Lugar, Hora)
%   visto_en(Persona, Lugar, Hora)     % camara o avistamiento confirmado
%
%   motivo(Persona, TipoMotivo)
%       TipoMotivo: deuda|herencia|venganza|celos|despido|encubrimiento|dinero
%
%   medio_requerido(Medio)             % lo que exigio el incidente
%   posee_medio(Persona, Medio)
%       Medio: llave|codigo_alarma|fuerza|conocimiento_tecnico|vehiculo|
%              veneno|herramienta
%
%   evidencia(IdEv, Tipo, Lugar, Hora, Descripcion)
%       Tipo: huella|adn|video|documento|objeto|registro|testimonio
%       Hora: entero 0..23 | desconocida
%   evidencia_incrimina(IdEv, Persona)
%
%   declaracion(IdDecl, Autor, Contenido)
%       Contenido tiene que ser uno de estos terminos, porque las reglas
%       detectan las contradicciones por unificacion sobre ellos:
%           estuvo_en(Persona, Lugar, Hora)
%           no_estuvo_en(Persona, Lugar, Hora)
%           vio_a(Persona, Lugar, Hora)
%           conoce_a(Persona1, Persona2)
%           no_conoce_a(Persona1, Persona2)
%           posee(Persona, Medio)
%
%   coartada(Persona, Lugar, Hora, Respaldo)
%       Respaldo: testigo(Persona)|camara(Lugar)|documento(IdEv)|ninguno


% =============================================================================
%  DECLARACIONES
% =============================================================================
%  Dinamicos para que las reglas funcionen aunque un caso todavia no defina el
%  predicado, y no salte existence_error.

:- dynamic caso/4.
:- dynamic sospechoso/1.
:- dynamic testigo/1.
:- dynamic victima/1.
:- dynamic relacion/3.
:- dynamic lugar/2.
:- dynamic escena_del_incidente/1.
:- dynamic hora_del_incidente/1.
:- dynamic lugar_conectado/2.
:- dynamic tiene_llave/2.
:- dynamic autorizado_en/2.
:- dynamic registro_acceso/3.
:- dynamic visto_en/3.
:- dynamic motivo/2.
:- dynamic medio_requerido/1.
:- dynamic posee_medio/2.
:- dynamic evidencia/5.
:- dynamic evidencia_incrimina/2.
:- dynamic declaracion/3.
:- dynamic coartada/4.

:- discontiguous regla_activada/3.


% =============================================================================
%  1. CONOCIMIENTO DEL DOMINIO (no depende del caso)
% =============================================================================

%! tipo_evidencia_directa(?Tipo) is nondet.
%  Tipos que ubican fisicamente a una persona. Solo estos contradicen una
%  declaracion: un testimonio no refuta a otro testimonio.
tipo_evidencia_directa(huella).
tipo_evidencia_directa(adn).
tipo_evidencia_directa(video).
tipo_evidencia_directa(registro).

%! relacion_conflictiva(?Tipo) is nondet.
%  Relaciones que por si mismas sugieren un motivo.
relacion_conflictiva(ex_pareja).
relacion_conflictiva(deudor).
relacion_conflictiva(rival).
relacion_conflictiva(heredero).

%! tolerancia_horaria(?Horas) is det.
%  Margen en horas para considerar dos momentos "el mismo momento".
tolerancia_horaria(1).

%! persona(?Persona) is nondet.
%  Cualquier involucrado en el caso.
persona(P) :- sospechoso(P).
persona(P) :- testigo(P), \+ sospechoso(P).
persona(P) :- victima(P), \+ sospechoso(P), \+ testigo(P).

%! horas_compatibles(+Hora1, +Hora2) is semidet.
%  Verdadero si los dos momentos caen en la misma ventana temporal. El corte
%  de la primera clausula evita repetir la aritmetica y una solucion duplicada.
horas_compatibles(H, H) :- !.
horas_compatibles(_, desconocida) :- !.   % evidencia sin hora: no discrimina
horas_compatibles(desconocida, _) :- !.
horas_compatibles(H1, H2) :-
    integer(H1), integer(H2),
    tolerancia_horaria(T),
    abs(H1 - H2) =< T.


% =============================================================================
%  2. LUGARES — RECURSIVIDAD SOBRE EL GRAFO DE ADYACENCIA
% =============================================================================

%! conectado(?Lugar1, ?Lugar2) is nondet.
%  lugar_conectado/2 se declara en un sentido; aqui se vuelve simetrico.
conectado(A, B) :- lugar_conectado(A, B).
conectado(A, B) :- lugar_conectado(B, A).

%! ruta(+Origen, +Destino, -Ruta) is nondet.
%  Camino entre dos lugares. Lleva la lista de lugares visitados porque el
%  grafo no es dirigido y sin ella la recursion no termina.
ruta(Origen, Destino, Ruta) :-
    ruta_(Origen, Destino, [Origen], Invertida),
    reverse(Invertida, Ruta).

ruta_(Destino, Destino, Visitados, Visitados).
ruta_(Actual, Destino, Visitados, Ruta) :-
    conectado(Actual, Siguiente),
    \+ member(Siguiente, Visitados),
    ruta_(Siguiente, Destino, [Siguiente|Visitados], Ruta).

%! alcanzable(+Origen, +Destino) is semidet.
%  Solo interesa si hay camino, no cual, asi que once/1 corta en el primero.
alcanzable(Origen, Destino) :-
    once(ruta(Origen, Destino, _)).


% =============================================================================
%  3. ACCESO, OPORTUNIDAD, MOTIVO Y MEDIOS
% =============================================================================

%! acceso_al_lugar(?Persona, ?Lugar) is nondet.
%  Una persona pudo entrar al lugar. Cuatro vias distintas: llave propia,
%  autorizacion por su rol, constancia en la bitacora de accesos, o acceso
%  indirecto por un lugar contiguo al que si tenia llave.
acceso_al_lugar(Persona, Lugar) :-
    tiene_llave(Persona, Lugar).
acceso_al_lugar(Persona, Lugar) :-
    autorizado_en(Persona, Lugar).
acceso_al_lugar(Persona, Lugar) :-
    registro_acceso(Persona, Lugar, _).
acceso_al_lugar(Persona, Lugar) :-
    tiene_llave(Persona, Origen),
    Origen \== Lugar,
    lugar(Lugar, _),
    alcanzable(Origen, Lugar).

%! presente_en_ventana(?Persona, ?Lugar) is nondet.
%  Hay constancia de que la persona estuvo en el lugar dentro de la ventana
%  temporal del incidente.
presente_en_ventana(Persona, Lugar) :-
    hora_del_incidente(Hora),
    visto_en(Persona, Lugar, HoraVisto),
    horas_compatibles(Hora, HoraVisto).
presente_en_ventana(Persona, Lugar) :-
    hora_del_incidente(Hora),
    registro_acceso(Persona, Lugar, HoraAcceso),
    horas_compatibles(Hora, HoraAcceso).

%! ubicado_fuera_de_la_escena(+Persona) is semidet.
%  La persona fue vista en otro lugar durante la ventana del incidente.
ubicado_fuera_de_la_escena(Persona) :-
    escena_del_incidente(Escena),
    hora_del_incidente(Hora),
    visto_en(Persona, Otro, HoraVisto),
    Otro \== Escena,
    horas_compatibles(Hora, HoraVisto).

%! tuvo_oportunidad(?Persona, ?Lugar) is nondet.
%  Pudo cometer el incidente: estuvo (o pudo estar) en la escena en el momento
%  del incidente y no tiene una coartada que lo descarte.
%
%  Clausula (a): hay constancia de su presencia en la escena.
tuvo_oportunidad(Persona, Lugar) :-
    escena_del_incidente(Lugar),
    persona(Persona),
    once(presente_en_ventana(Persona, Lugar)),
    \+ coartada_valida(Persona, _).
%  Clausula (b): no hay constancia de su presencia, pero tenia acceso y nadie
%  lo ubica en otro lugar a esa hora.
tuvo_oportunidad(Persona, Lugar) :-
    escena_del_incidente(Lugar),
    persona(Persona),
    acceso_al_lugar(Persona, Lugar),
    \+ presente_en_ventana(Persona, Lugar),
    \+ ubicado_fuera_de_la_escena(Persona),
    \+ coartada_valida(Persona, _).

%! tiene_motivo(?Persona, ?Motivo) is nondet.
%  Motivo declarado como hecho, o derivado de una relacion conflictiva con la
%  victima.
tiene_motivo(Persona, Motivo) :-
    motivo(Persona, Motivo).
tiene_motivo(Persona, conflicto_con_la_victima(Tipo)) :-
    victima(Victima),
    Persona \== Victima,
    relacion_bidireccional(Persona, Victima, Tipo),
    relacion_conflictiva(Tipo).

%! relacion_bidireccional(?Persona1, ?Persona2, ?Tipo) is nondet.
relacion_bidireccional(A, B, Tipo) :- relacion(A, B, Tipo).
relacion_bidireccional(A, B, Tipo) :- relacion(B, A, Tipo).

%! tiene_medios(?Persona, ?Medio) is nondet.
%  Contaba con lo que el incidente exigio. Solo cuentan los medios declarados
%  como requeridos: un vehiculo no importa si el incidente no necesito uno.
tiene_medios(Persona, Medio) :-
    medio_requerido(Medio),
    posee_medio(Persona, Medio).
tiene_medios(Persona, llave) :-
    medio_requerido(llave),
    escena_del_incidente(Escena),
    tiene_llave(Persona, Escena).


% =============================================================================
%  4. COARTADAS
% =============================================================================

%! respaldo_confiable(+Respaldo) is semidet.
%  Un testigo que tambien es sospechoso, o que ya se comprobo que mintio, no
%  respalda nada.
respaldo_confiable(testigo(T)) :-
    testigo(T),
    \+ sospechoso(T),
    \+ informacion_falsa(T).
respaldo_confiable(camara(Lugar)) :-
    lugar(Lugar, _).
respaldo_confiable(documento(IdEv)) :-
    evidencia(IdEv, _, _, _, _).

%! coartada_contradicha(+Persona, +Lugar, +Hora) is semidet.
%  Algo ubica a la persona en otro lugar a la hora que dice su coartada.
coartada_contradicha(Persona, Lugar, Hora) :-
    evidencia(IdEv, Tipo, OtroLugar, HoraEv, _),
    tipo_evidencia_directa(Tipo),
    evidencia_incrimina(IdEv, Persona),
    OtroLugar \== Lugar,
    horas_compatibles(Hora, HoraEv).
coartada_contradicha(Persona, Lugar, Hora) :-
    visto_en(Persona, OtroLugar, HoraVisto),
    OtroLugar \== Lugar,
    horas_compatibles(Hora, HoraVisto).

%! coartada_valida(?Persona, ?Justificacion) is nondet.
%  La coartada tiene respaldo confiable y nada la contradice.
coartada_valida(Persona, respaldada_por(Respaldo)) :-
    coartada(Persona, Lugar, Hora, Respaldo),
    Respaldo \== ninguno,
    respaldo_confiable(Respaldo),
    \+ coartada_contradicha(Persona, Lugar, Hora).

%! coartada_invalida(?Persona, ?Razon) is nondet.
%  Cuatro formas de que una coartada no sirva. Devuelve la razon, que es lo
%  que muestra la interfaz.
coartada_invalida(Persona, no_presento_coartada) :-
    sospechoso(Persona),
    \+ coartada(Persona, _, _, _).
coartada_invalida(Persona, sin_respaldo) :-
    coartada(Persona, _, _, ninguno).
coartada_invalida(Persona, respaldo_no_confiable(Respaldo)) :-
    coartada(Persona, _, _, Respaldo),
    Respaldo \== ninguno,
    \+ respaldo_confiable(Respaldo).
coartada_invalida(Persona, contradicha_por(Lugar, Hora)) :-
    coartada(Persona, Lugar, Hora, _),
    % once/1 porque aqui Lugar y Hora ya estan ligados por coartada/4: basta
    % con saber que algo contradice esa coartada. Sin el corte, la misma razon
    % sale repetida una vez por cada hecho que la contradice.
    once(coartada_contradicha(Persona, Lugar, Hora)).


% =============================================================================
%  5. CONTRADICCIONES E INFORMACION FALSA
% =============================================================================
%  No se declaran como hechos: se deducen comparando el contenido de las
%  declaraciones por unificacion. El caso aporta las declaraciones y el motor
%  encuentra los choques.

%! declaracion_contradice_declaracion(?IdDecl1, ?IdDecl2) is nondet.
%  Cuatro patrones de contradiccion entre dos declaraciones.

%  (a) Ubican a la misma persona en dos lugares distintos al mismo tiempo.
declaracion_contradice_declaracion(D1, D2) :-
    declaracion(D1, _, estuvo_en(Persona, Lugar1, Hora1)),
    declaracion(D2, _, estuvo_en(Persona, Lugar2, Hora2)),
    D1 \== D2,
    Lugar1 \== Lugar2,
    horas_compatibles(Hora1, Hora2).
%  (b) Una afirma y la otra niega la misma presencia.
declaracion_contradice_declaracion(D1, D2) :-
    declaracion(D1, _, estuvo_en(Persona, Lugar, Hora1)),
    declaracion(D2, _, no_estuvo_en(Persona, Lugar, Hora2)),
    horas_compatibles(Hora1, Hora2).
%  (c) Alguien dice haber visto a una persona que niega haber estado ahi.
declaracion_contradice_declaracion(D1, D2) :-
    declaracion(D1, _, vio_a(Persona, Lugar, Hora1)),
    declaracion(D2, _, no_estuvo_en(Persona, Lugar, Hora2)),
    horas_compatibles(Hora1, Hora2).
%  (d) Una afirma y la otra niega que dos personas se conozcan.
declaracion_contradice_declaracion(D1, D2) :-
    declaracion(D1, _, conoce_a(A, B)),
    declaracion(D2, _, no_conoce_a(X, Y)),
    mismo_par(A, B, X, Y).

%! mismo_par(+A, +B, +X, +Y) is semidet.
%  "A conoce a B" y "B conoce a A" son la misma afirmacion.
mismo_par(A, B, A, B) :- !.
mismo_par(A, B, B, A).

%! declaracion_contradice_evidencia(?IdDecl, ?IdEv) is nondet.
%  Una declaracion choca con evidencia fisica. Solo refuta la evidencia
%  directa (huella, adn, video, registro); un testimonio no basta.

%  (a) Niega haber estado donde la evidencia lo ubica.
declaracion_contradice_evidencia(IdDecl, IdEv) :-
    declaracion(IdDecl, _, no_estuvo_en(Persona, Lugar, Hora)),
    evidencia(IdEv, Tipo, Lugar, HoraEv, _),
    tipo_evidencia_directa(Tipo),
    evidencia_incrimina(IdEv, Persona),
    horas_compatibles(Hora, HoraEv).
%  (b) Afirma haber estado en un lugar mientras la evidencia lo ubica en otro.
declaracion_contradice_evidencia(IdDecl, IdEv) :-
    declaracion(IdDecl, _, estuvo_en(Persona, Lugar, Hora)),
    evidencia(IdEv, Tipo, OtroLugar, HoraEv, _),
    tipo_evidencia_directa(Tipo),
    evidencia_incrimina(IdEv, Persona),
    OtroLugar \== Lugar,
    horas_compatibles(Hora, HoraEv).
%  (c) Niega conocer a alguien con quien el caso registra una relacion.
declaracion_contradice_evidencia(IdDecl, IdEv) :-
    declaracion(IdDecl, _, no_conoce_a(A, B)),
    relacion_bidireccional(A, B, _),
    evidencia(IdEv, documento, _, _, _),
    evidencia_incrimina(IdEv, A).

%! informacion_falsa(?Persona) is nondet.
%  La persona mintio y se puede probar. Si dos personas se contradicen entre
%  si no se sabe cual de las dos miente, asi que ese caso no cuenta aqui; lo
%  reporta declaracion_contradice_declaracion/2.
%
%  El corte deja el predicado semidet: basta una mentira comprobada, y sin el
%  la persona saldria repetida una vez por cada declaracion contradicha.
informacion_falsa(Persona) :-
    persona(Persona),
    declaracion(IdDecl, Persona, _),
    declaracion_contradice_evidencia(IdDecl, _),
    !.
informacion_falsa(Persona) :-
    persona(Persona),
    declaracion(D1, Persona, _),
    declaracion(D2, Persona, _),
    D1 \== D2,
    declaracion_contradice_declaracion(D1, D2),
    !.

%! contradicciones(-Lista) is det.
%  Todas las contradicciones del caso, sin repetidos, para la interfaz.
%  El par se normaliza con sort/2 antes de recolectarlo, porque los patrones
%  (b) y (c) son direccionales y el mismo choque puede llegar en cualquiera de
%  los dos ordenes. De paso, sort/2 sobre [D,D] devuelve [D], que no unifica
%  con [A,B], asi que una declaracion no se contradice a si misma.
contradicciones(Lista) :-
    findall(entre_declaraciones(A, B),
            ( declaracion_contradice_declaracion(D1, D2),
              sort([D1, D2], [A, B])
            ),
            Entre),
    findall(declaracion_vs_evidencia(D, E),
            declaracion_contradice_evidencia(D, E),
            Contra),
    append(Entre, Contra, Todas),
    sort(Todas, Lista).


% =============================================================================
%  6. EVIDENCIAS POR SOSPECHOSO
% =============================================================================

%! evidencia_contra(?Persona, ?IdEv) is nondet.
evidencia_contra(Persona, IdEv) :-
    evidencia_incrimina(IdEv, Persona).

%! evidencia_directa_contra(?Persona, ?IdEv) is nondet.
evidencia_directa_contra(Persona, IdEv) :-
    evidencia_incrimina(IdEv, Persona),
    evidencia(IdEv, Tipo, _, _, _),
    tipo_evidencia_directa(Tipo).

%! evidencias_contra(+Persona, -Lista) is det.
evidencias_contra(Persona, Lista) :-
    findall(IdEv, evidencia_contra(Persona, IdEv), Sin),
    sort(Sin, Lista).


% =============================================================================
%  7. NIVEL DE SOSPECHA — LISTAS + RECURSION + CORTES
% =============================================================================

%! indicio(?Persona, ?Indicio) is nondet.
%  Cada indicio que el motor puede detectar contra una persona.
indicio(Persona, acceso) :-
    escena_del_incidente(Escena),
    persona(Persona),
    once(acceso_al_lugar(Persona, Escena)).
indicio(Persona, oportunidad) :-
    persona(Persona),
    once(tuvo_oportunidad(Persona, _)).
indicio(Persona, motivo) :-
    persona(Persona),
    once(tiene_motivo(Persona, _)).
indicio(Persona, medios) :-
    persona(Persona),
    once(tiene_medios(Persona, _)).
indicio(Persona, coartada_invalida) :-
    persona(Persona),
    once(coartada_invalida(Persona, _)).
indicio(Persona, informacion_falsa) :-
    informacion_falsa(Persona).
indicio(Persona, evidencia_directa) :-
    persona(Persona),
    once(evidencia_directa_contra(Persona, _)).
indicio(Persona, multiples_evidencias) :-
    persona(Persona),
    evidencias_contra(Persona, Evidencias),
    length(Evidencias, N),
    N >= 2.

%! peso(?Indicio, ?Puntos) is nondet.
%  Cuanto aporta cada indicio. La evidencia fisica y la mentira comprobada
%  pesan mas que el acceso, que casi cualquiera tiene.
peso(acceso, 1).
peso(oportunidad, 2).
peso(motivo, 2).
peso(medios, 2).
peso(coartada_invalida, 3).
peso(informacion_falsa, 3).
peso(evidencia_directa, 3).
peso(multiples_evidencias, 2).

%! indicios(+Persona, -Lista) is det.
%  Lista ordenada y sin repetidos de los indicios contra una persona.
indicios(Persona, Lista) :-
    findall(Indicio, indicio(Persona, Indicio), Sin),
    sort(Sin, Lista).

%! suma_pesos(+Indicios, -Total) is det.
%  Recorrido recursivo de la lista de indicios acumulando su peso.
suma_pesos([], 0).
suma_pesos([Indicio|Resto], Total) :-
    peso(Indicio, Puntos),
    suma_pesos(Resto, Subtotal),
    Total is Subtotal + Puntos.

%! puntaje_sospecha(?Persona, -Puntaje) is nondet.
puntaje_sospecha(Persona, Puntaje) :-
    persona(Persona),
    indicios(Persona, Indicios),
    suma_pesos(Indicios, Puntaje).

%! nivel_sospecha(?Persona, -Nivel) is nondet.
%  Nivel: muy_alto | alto | medio | bajo | nulo.
nivel_sospecha(Persona, Nivel) :-
    puntaje_sospecha(Persona, Puntaje),
    clasificar_sospecha(Puntaje, Nivel).

%! clasificar_sospecha(+Puntaje, -Nivel) is det.
%  Clasificacion por rangos. El corte va antes de unificar Nivel: la
%  comparacion decide la clausula y la salida se construye despues. Si el corte
%  fuera despues, clasificar_sospecha(15, nulo) tendria exito.
clasificar_sospecha(Puntaje, Nivel) :- Puntaje >= 12, !, Nivel = muy_alto.
clasificar_sospecha(Puntaje, Nivel) :- Puntaje >= 8,  !, Nivel = alto.
clasificar_sospecha(Puntaje, Nivel) :- Puntaje >= 4,  !, Nivel = medio.
clasificar_sospecha(Puntaje, Nivel) :- Puntaje >= 1,  !, Nivel = bajo.
clasificar_sospecha(_, nulo).

%! ranking_sospecha(-Ranking) is det.
%  Sospechosos ordenados de mayor a menor puntaje: lista de
%  sospecha(Puntaje, Persona, Nivel).
ranking_sospecha(Ranking) :-
    findall(Puntaje-Persona,
            ( sospechoso(Persona), puntaje_sospecha(Persona, Puntaje) ),
            Pares),
    sort(0, @>=, Pares, Ordenados),
    pares_a_sospechas(Ordenados, Ranking).

%! pares_a_sospechas(+Pares, -Sospechas) is det.
%  Recursion que convierte la lista intermedia Puntaje-Persona en terminos con
%  el nivel ya clasificado.
pares_a_sospechas([], []).
pares_a_sospechas([Puntaje-Persona|Resto], [sospecha(Puntaje, Persona, Nivel)|Otras]) :-
    clasificar_sospecha(Puntaje, Nivel),
    pares_a_sospechas(Resto, Otras).


% =============================================================================
%  8. CONCLUSIONES
% =============================================================================

%! sospechoso_principal(?Persona) is nondet.
%  El sospechoso con el puntaje mas alto. Si hay empate devuelve a todos los
%  empatados en vez de elegir uno.
sospechoso_principal(Persona) :-
    sospechoso(Persona),
    puntaje_sospecha(Persona, Puntaje),
    Puntaje > 0,
    \+ ( sospechoso(Otro),
         Otro \== Persona,
         puntaje_sospecha(Otro, OtroPuntaje),
         OtroPuntaje > Puntaje
       ).

%! responsable(?Persona) is semidet.
%  Conclusion del caso. Pide oportunidad, motivo y medios, sin coartada
%  valida, con al menos dos evidencias en contra y sin empate con otro
%  sospechoso. Nunca concluye con una sola evidencia.
%
%  El corte final lo deja semidet: el caso tiene un solo responsable y no hace
%  falta buscar otras derivaciones del mismo hecho.
responsable(Persona) :-
    sospechoso_principal(Persona),
    \+ ( sospechoso_principal(Otro), Otro \== Persona ),
    tuvo_oportunidad(Persona, _),
    tiene_motivo(Persona, _),
    tiene_medios(Persona, _),
    \+ coartada_valida(Persona, _),
    evidencias_contra(Persona, Evidencias),
    length(Evidencias, N),
    N >= 2,
    !.

%! posible_complice(?Complice, ?Principal) is nondet.
%  Sin ser el responsable, tiene relacion con el sospechoso principal y
%  ademas mintio o le sostuvo una coartada que no se sostiene.
posible_complice(Complice, Principal) :-
    sospechoso_principal(Principal),
    persona(Complice),
    Complice \== Principal,
    \+ responsable(Complice),
    once(relacion_bidireccional(Complice, Principal, _)),
    once(( informacion_falsa(Complice)
         ; respalda_coartada_de(Complice, Principal)
         )).

%! respalda_coartada_de(?Testigo, ?Persona) is nondet.
%  El testigo respalda una coartada que el motor no considera valida.
respalda_coartada_de(Testigo, Persona) :-
    coartada(Persona, _, _, testigo(Testigo)),
    \+ coartada_valida(Persona, _).


% =============================================================================
%  9. EXPLICACION DEL RAZONAMIENTO
% =============================================================================
%  regla_activada/3 emite un termino por cada regla que tuvo exito para la
%  persona, con el detalle que la disparo. Es la justificacion de la conclusion.

regla_activada(Persona, acceso_al_lugar, Lugar) :-
    escena_del_incidente(Escena),
    once(acceso_al_lugar(Persona, Escena)),
    Lugar = Escena.
regla_activada(Persona, tuvo_oportunidad, Lugar) :-
    once(tuvo_oportunidad(Persona, Lugar)).
regla_activada(Persona, tiene_motivo, Motivo) :-
    tiene_motivo(Persona, Motivo).
regla_activada(Persona, tiene_medios, Medio) :-
    tiene_medios(Persona, Medio).
regla_activada(Persona, coartada_valida, Justificacion) :-
    coartada_valida(Persona, Justificacion).
regla_activada(Persona, coartada_invalida, Razon) :-
    coartada_invalida(Persona, Razon).
regla_activada(Persona, informacion_falsa, comprobada) :-
    informacion_falsa(Persona).
regla_activada(Persona, declaracion_contradice_evidencia, IdDecl-IdEv) :-
    declaracion(IdDecl, Persona, _),
    declaracion_contradice_evidencia(IdDecl, IdEv).
regla_activada(Persona, declaracion_contradice_declaracion, IdDecl1-IdDecl2) :-
    declaracion(IdDecl1, Persona, _),
    declaracion_contradice_declaracion(IdDecl1, IdDecl2).
regla_activada(Persona, evidencia_directa_contra, IdEv) :-
    evidencia_directa_contra(Persona, IdEv).
regla_activada(Persona, posible_complice, De) :-
    posible_complice(Persona, De).

%! explicacion(?Persona, -Explicacion) is nondet.
%  Traza de razonamiento: lista de regla(Nombre, Detalle) con las reglas que se
%  activaron, y al final un termino conclusion(Veredicto, Nivel, Puntaje).
%
%      ?- caso1:explicacion(P, E).
%
explicacion(Persona, Explicacion) :-
    persona(Persona),
    findall(regla(Nombre, Detalle),
            regla_activada(Persona, Nombre, Detalle),
            Reglas0),
    sort(Reglas0, Reglas),
    puntaje_sospecha(Persona, Puntaje),
    clasificar_sospecha(Puntaje, Nivel),
    veredicto(Persona, Veredicto),
    append(Reglas, [conclusion(Veredicto, Nivel, Puntaje)], Explicacion).

%! veredicto(+Persona, -Veredicto) is det.
%  responsable | sospechoso_principal | bajo_investigacion | descartado
veredicto(Persona, Veredicto) :-
    responsable(Persona), !,
    Veredicto = responsable.
veredicto(Persona, Veredicto) :-
    sospechoso_principal(Persona), !,
    Veredicto = sospechoso_principal.
veredicto(Persona, Veredicto) :-
    puntaje_sospecha(Persona, Puntaje),
    Puntaje > 0, !,
    Veredicto = bajo_investigacion.
veredicto(_, descartado).


% =============================================================================
%  10. APOYO A LA INTERFAZ
% =============================================================================

%! linea_temporal(-Eventos) is det.
%  Todo lo que el caso sabe que paso, ordenado por hora.
linea_temporal(Eventos) :-
    findall(Hora-evento(Hora, Tipo, Detalle),
            evento_registrado(Hora, Tipo, Detalle),
            Pares),
    keysort(Pares, Ordenados),
    pairs_values(Ordenados, Eventos).

evento_registrado(Hora, presencia, visto_en(Persona, Lugar)) :-
    visto_en(Persona, Lugar, Hora),
    integer(Hora).
evento_registrado(Hora, acceso, registro_acceso(Persona, Lugar)) :-
    registro_acceso(Persona, Lugar, Hora),
    integer(Hora).
evento_registrado(Hora, evidencia, evidencia(IdEv, Lugar)) :-
    evidencia(IdEv, _, Lugar, Hora, _),
    integer(Hora).
evento_registrado(Hora, incidente, escena(Lugar)) :-
    hora_del_incidente(Hora),
    escena_del_incidente(Lugar).

%! pista(-Pista) is nondet.
%  Sugerencias de que revisar, derivadas del estado del razonamiento.
pista(revisar_coartada_de(Persona)) :-
    sospechoso(Persona),
    once(coartada_invalida(Persona, _)).
pista(revisar_declaraciones_de(Persona)) :-
    informacion_falsa(Persona).
pista(revisar_evidencia(IdEv)) :-
    evidencia_directa_contra(_, IdEv).
pista(revisar_relacion_con_la_victima(Persona)) :-
    victima(Victima),
    relacion_bidireccional(Persona, Victima, Tipo),
    relacion_conflictiva(Tipo).

%! resumen_caso(-Resumen) is det.
%  Conteos para el modulo administrativo y para verificar los minimos.
resumen_caso(resumen(Sospechosos, Evidencias, Lugares, Declaraciones, Coartadas)) :-
    contar(sospechoso(_), Sospechosos),
    contar(evidencia(_, _, _, _, _), Evidencias),
    contar(lugar(_, _), Lugares),
    contar(declaracion(_, _, _), Declaraciones),
    contar(coartada(_, _, _, _), Coartadas).

%! contar(+Meta, -Cuantos) is det.
contar(Meta, Cuantos) :-
    findall(x, Meta, Lista),
    length(Lista, Cuantos).
