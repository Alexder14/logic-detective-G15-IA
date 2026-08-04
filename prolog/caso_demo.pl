% =============================================================================
%  CASO DEMO — EJEMPLO DE REFERENCIA
% =============================================================================
%
%  ESTE NO ES UNO DE LOS TRES CASOS ENTREGABLES.
%
%  Existe por dos razones:
%    1. Probar de punta a punta que la integracion funciona (interfaz ->
%       backend -> PySwip -> Prolog) mientras caso1/caso2/caso3 estan vacios.
%    2. Servir de ejemplo minimo de como se escribe un caso.
%
%  Es chico (3 sospechosos, 5 evidencias) y no cumple los minimos del
%  enunciado. Usalo como referencia de formato, no de tamano. El esquema
%  completo de hechos esta en el encabezado de reglas_base.pl.
%
%  Consulta directa:
%      swipl prolog/caso_demo.pl
%      ?- caso_demo:responsable(P).
%      ?- caso_demo:explicacion(bruno, E), forall(member(R,E), (print(R), nl)).
%
% =============================================================================

:- module(caso_demo, []).

:- include('reglas_base.pl').


% --- Identidad ---------------------------------------------------------------
caso(caso_demo,
     'Ejemplo: la laptop del laboratorio',
     'Desapareció una laptop del laboratorio de cómputo entre las 13:00 y las 15:00. Caso de demostración del motor de inferencia.',
     facil).

% --- Personas ---------------------------------------------------------------
sospechoso(ana).
sospechoso(bruno).
sospechoso(carla).

testigo(don_luis).          % conserje del edificio

victima(prof_mendez).

relacion(bruno, prof_mendez, deudor).
relacion(ana, bruno, vecino).
relacion(carla, bruno, amigo).

% --- Lugares y tiempo -------------------------------------------------------
lugar(laboratorio, 'Laboratorio de cómputo, segundo nivel').
lugar(pasillo,     'Pasillo del segundo nivel').
lugar(recepcion,   'Recepción del edificio').
lugar(bodega,      'Bodega de equipo').
lugar(parqueo,     'Parqueo de visitantes').

escena_del_incidente(laboratorio).
hora_del_incidente(14).

lugar_conectado(laboratorio, pasillo).
lugar_conectado(pasillo, recepcion).
lugar_conectado(pasillo, bodega).
lugar_conectado(recepcion, parqueo).

% --- Acceso -----------------------------------------------------------------
tiene_llave(bruno, laboratorio).
tiene_llave(ana, recepcion).        % acceso indirecto al laboratorio vía ruta/3
autorizado_en(ana, laboratorio).
registro_acceso(carla, laboratorio, 13).

% --- Presencia --------------------------------------------------------------
visto_en(bruno, laboratorio, 14).
visto_en(ana, recepcion, 14).
visto_en(don_luis, pasillo, 14).

% --- Motivo -----------------------------------------------------------------
motivo(bruno, deuda).

% --- Medios -----------------------------------------------------------------
medio_requerido(llave).
posee_medio(bruno, llave).

% --- Evidencias -------------------------------------------------------------
evidencia(e1, huella,    laboratorio, 14,          'Huella en el escritorio donde estaba la laptop').
evidencia(e2, video,     pasillo,     14,          'Cámara del pasillo graba a alguien saliendo con un maletín').
evidencia(e3, objeto,    bodega,      desconocida, 'Empaque vacío de la laptop').
evidencia(e4, documento, recepcion,   13,          'Bitácora de visitantes del día').
evidencia(e5, testimonio, pasillo,    14,          'Testimonio del conserje').

evidencia_incrimina(e1, bruno).
evidencia_incrimina(e2, bruno).
evidencia_incrimina(e3, carla).
evidencia_incrimina(e5, bruno).

% --- Declaraciones ----------------------------------------------------------
declaracion(d1, bruno,    no_estuvo_en(bruno, laboratorio, 14)).
declaracion(d2, don_luis, vio_a(bruno, laboratorio, 14)).
declaracion(d3, ana,      estuvo_en(ana, recepcion, 14)).
declaracion(d4, carla,    estuvo_en(bruno, laboratorio, 14)).

% --- Coartadas --------------------------------------------------------------
coartada(ana,   recepcion, 14, testigo(don_luis)).   % válida
coartada(bruno, parqueo,   14, ninguno).             % sin respaldo
coartada(carla, bodega,    13, testigo(bruno)).      % respaldo no confiable
