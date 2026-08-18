% =============================================================================
%  CASO 3 — El servidor saboteado
%  Responsable: Joshua Estuardo Franco Equite
% =============================================================================
%
%  AVANCE — SEMANA 1 (03-07 ago)
%  ---------------------------------------------------------------------------
%  Sospechosos, lugares, relaciones, acceso, presencia, motivo, medios y
%  coartadas. diego_lira quedo como sospechoso principal (acceso + oportunidad
%  + motivo + medios + coartada_invalida), sin empatar con los otros tres.
%
%  AVANCE — SEMANA 2 (08-15 ago)
%  ---------------------------------------------------------------------------
%  Se completan las evidencias, las declaraciones y las 10 reglas propias del
%  caso (sección al final). Con esto `responsable(diego_lira)` ya concluye:
%  tiene sus dos evidencias minimas (le tocaron 4) y ninguno de los otros tres
%  llega a empatarlo. Probar:
%
%      swipl prolog/caso3.pl
%      ?- caso3:responsable(P).            % debe dar diego_lira, UNA sola vez
%      ?- caso3:ranking_sospecha(R).        % diego_lira primero, y lejos
%      ?- caso3:contradicciones(C).         % d1 contra e1 y e3
%
%  ARCHIVO COMPLETO en hechos y reglas propias. Las reglas de inferencia
%  compartidas ya están resueltas en reglas_base.pl y este archivo las hereda
%  con `:- include`. NO copies reglas_base.pl aquí y NO la edites: si
%  necesitas un predicado que no existe, habla con el coordinador.
%
%  ---------------------------------------------------------------------------
%  MÍNIMOS QUE EXIGE EL ENUNCIADO PARA ESTE CASO
%  ---------------------------------------------------------------------------
%
%    [x]  4 sospechosos      -> sospechoso/1
%    [x] 10 evidencias       -> evidencia/5  (+ evidencia_incrimina/2)
%    [x]  5 lugares          -> lugar/2
%    [x]  5 declaraciones    -> declaracion/3
%    [x] 10 reglas de inferencia propias del caso (sección al final)
%
%  Además, para que el motor pueda concluir algo, este caso NECESITA:
%
%    [x] caso/4                    identidad del caso (ya está abajo)
%    [x] victima/1                 quién sufrió el incidente
%    [x] escena_del_incidente/1    dónde ocurrió
%    [x] hora_del_incidente/1      entero 0..23
%    [x] medio_requerido/1         qué exigió el incidente (al menos uno)
%    [x] coartada/4                una por sospechoso, con o sin respaldo
%    [x] relacion/3                relaciones entre los involucrados
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
caso(caso3,
     'El servidor saboteado',
     'A las 2:00 a.m., durante una ventana de mantenimiento, alguien corrompió deliberadamente los archivos de configuración del servidor principal de NexaCorp, tirando el sistema y arruinando la migración que lideraba la ingeniera Paola Ríos. ¿Quién tuvo acceso a la sala de servidores esa noche, y por qué?',
     media).


% --- Personas ---------------------------------------------------------------
%  sospechoso/1, testigo/1, victima/1, relacion/3
%
%  4 sospechosos, todos con llegada plausible a la sala de servidores:
%    diego_lira     contratista de TI, le avisaron que no le renuevan
%    renata_soto    sysadmin, le debe dinero a la victima (deudor: relacion
%                   conflictiva -> tiene_motivo se deriva sola, no hace falta
%                   un motivo/2 aparte para ella)
%    bruno_paredes  guardia de seguridad, acceso a todo el edificio
%    ana_lucero     sysadmin junior, amiga de la victima, se fue temprano

sospechoso(diego_lira).
sospechoso(renata_soto).
sospechoso(bruno_paredes).
sospechoso(ana_lucero).

testigo(carlos_vega).            % guardia del turno nocturno, no es sospechoso

victima(paola_rios).             % jefa de sistemas, responsable del proyecto perdido

relacion(diego_lira,    paola_rios, empleado).   % contratista bajo su supervision
relacion(renata_soto,   paola_rios, deudor).     % conflictiva -> motivo derivado
relacion(bruno_paredes, paola_rios, empleado).
relacion(ana_lucero,    paola_rios, amigo).
relacion(renata_soto,   diego_lira, amigo).      % se conocen fuera del trabajo (semana 2: vinculado_con/2)


% --- Lugares y tiempo -------------------------------------------------------
%  lugar/2, escena_del_incidente/1, hora_del_incidente/1, lugar_conectado/2
%
%  Cadena sala_servidores - pasillo - {oficina_ti, recepcion} - estacionamiento.
%  Nadie necesita la adyacencia para llegar a la escena (todos los que tienen
%  acceso lo tienen directo), pero queda para que `alcanzable/2` tenga algo
%  que recorrer si alguien prueba consultas de ruta.

lugar(sala_servidores,    'Sala de servidores principal de NexaCorp').
lugar(oficina_ti,         'Oficina del equipo de TI, contigua a la sala de servidores').
lugar(pasillo_datacenter, 'Pasillo de acceso restringido del datacenter').
lugar(recepcion,          'Recepción y caseta de vigilancia del edificio').
lugar(estacionamiento,    'Estacionamiento de empleados').

escena_del_incidente(sala_servidores).
hora_del_incidente(2).

lugar_conectado(sala_servidores, pasillo_datacenter).
lugar_conectado(pasillo_datacenter, oficina_ti).
lugar_conectado(pasillo_datacenter, recepcion).
lugar_conectado(recepcion, estacionamiento).


% --- Acceso -----------------------------------------------------------------
%  tiene_llave/2, autorizado_en/2, registro_acceso/3
%
%  diego_lira es el UNICO con tiene_llave directo a la escena: eso le da
%  acceso_al_lugar/2 por la primera clausula de reglas_base, sin necesitar la
%  ruta recursiva. bruno tiene autorizado_en (acceso, pero a todo el
%  edificio, no prueba nada por si solo). renata y ana solo tienen
%  registro_acceso a oficina_ti, un lugar distinto de la escena: acceso_al_lugar
%  exige que el lugar del registro sea la escena, asi que a ellas NO les
%  cuenta como acceso a sala_servidores.

tiene_llave(diego_lira, sala_servidores).
autorizado_en(bruno_paredes, sala_servidores).
registro_acceso(diego_lira, oficina_ti, 1).      % paso por su oficina antes de ir a la escena
registro_acceso(renata_soto, oficina_ti, 1).
registro_acceso(ana_lucero, oficina_ti, 23).


% --- Presencia --------------------------------------------------------------
%  visto_en/3
%
%  A bruno lo capta la camara de recepcion A LA MISMA HORA del incidente, en
%  otro lugar: eso activa ubicado_fuera_de_la_escena/1 y le bloquea la
%  oportunidad aunque tenga acceso. A diego, en cambio, nadie lo ve en ningun
%  lado esa noche -- ni en la escena ni fuera de ella -- que es justo el hueco
%  que la clausula (b) de tuvo_oportunidad/2 esta pensada para cubrir.

visto_en(bruno_paredes, recepcion, 2).


% --- Motivo -----------------------------------------------------------------
%  motivo/2
%
%  El de renata_soto no hace falta declararlo aqui: sale solo de la relacion
%  deudor con la victima (ver mas arriba, y tiene_motivo/2 en reglas_base).

motivo(diego_lira, despido).


% --- Medios -----------------------------------------------------------------
%  medio_requerido/1, posee_medio/2
%
%  El sabotaje pudo hacerse con acceso fisico a la consola (llave) o de forma
%  remota si sabias lo que estabas tocando (conocimiento_tecnico). diego_lira
%  cumple las dos: la de llave se la da gratis reglas_base (tiene_llave en la
%  escena + medio_requerido(llave)); la de conocimiento_tecnico se declara
%  aqui porque el motor no la puede derivar de otro hecho. renata_soto
%  tambien es sysadmin y tiene conocimiento_tecnico -- le suma un indicio de
%  "medios" en el ranking, pero su coartada valida (ver abajo) la mantiene
%  lejos de tuvo_oportunidad/2.

medio_requerido(llave).
medio_requerido(conocimiento_tecnico).

posee_medio(diego_lira, conocimiento_tecnico).
posee_medio(renata_soto, conocimiento_tecnico).


% --- Evidencias -------------------------------------------------------------
%  evidencia/5, evidencia_incrimina/2
%
%  e1-e4 contra diego_lira (huella, video y registro son tipos "directos" de
%  reglas_base: contradicen coartadas y declaraciones por si solos). e5, e6 y
%  e10 son de contexto, sin acusar a nadie en particular. e7-e9 son indicios
%  circunstanciales -- uno por cada distractor -- pero ninguno es de tipo
%  directo ni llega a dos por persona, asi que no les suma puntaje en el
%  ranking (ver evidencia_directa/multiples_evidencias en reglas_base).

evidencia(e1, huella,     sala_servidores,    2,           'Huella latente en el teclado de la consola principal').
evidencia(e2, video,      pasillo_datacenter, 2,           'La camara del pasillo capta a alguien con gafete de contratista entrando a la sala de servidores').
evidencia(e3, registro,   sala_servidores,    2,           'Bitacora del sistema: sesion remota de mantenimiento abierta con las credenciales de diego_lira').
evidencia(e4, documento,  oficina_ti,         desconocida, 'Correo de Recursos Humanos: el contrato de diego_lira queda marcado como "no renovar"').
evidencia(e5, testimonio, recepcion,          2,           'Carlos Vega declara que nadie entro por la puerta principal esa noche').
evidencia(e6, objeto,     sala_servidores,    desconocida, 'Memoria USB sin identificar conectada al puerto de la consola').
evidencia(e7, documento,  oficina_ti,         desconocida, 'Historial de chat interno: renata_soto se queja de la deuda que le exige la victima').
evidencia(e8, testimonio, pasillo_datacenter, desconocida, 'Un companero recuerda a bruno_paredes revisando la puerta de la sala de servidores en una ronda anterior').
evidencia(e9, documento,  oficina_ti,         desconocida, 'Un correo muestra que ana_lucero pidio el manual de administracion del servidor la semana anterior, aunque no es su area').
evidencia(e10, objeto,    sala_servidores,    desconocida, 'El servidor de respaldo no fue tocado: el ataque fue selectivo, no vandalismo al azar').

evidencia_incrimina(e1, diego_lira).
evidencia_incrimina(e2, diego_lira).
evidencia_incrimina(e3, diego_lira).
evidencia_incrimina(e4, diego_lira).
evidencia_incrimina(e7, renata_soto).
evidencia_incrimina(e8, bruno_paredes).
evidencia_incrimina(e9, ana_lucero).


% --- Declaraciones ----------------------------------------------------------
%  declaracion/3
%
%  d1 es la mentira del caso: diego_lira niega haber estado en la escena, y
%  e1/e3 (huella y registro, ambas directas, mismo lugar y hora) la
%  contradicen por declaracion_contradice_evidencia/2 de reglas_base, asi que
%  informacion_falsa(diego_lira) tambien se activa. d2 es un testigo
%  independiente que lo ubica llegando. d3 y d4 son las versiones de bruno y
%  renata, consistentes con sus propios registros y coartadas. d5 es un dato
%  suelto de ana_lucero, sin contradiccion, para variar el tipo de termino.

declaracion(d1, diego_lira,    no_estuvo_en(diego_lira, sala_servidores, 2)).
declaracion(d2, carlos_vega,   vio_a(diego_lira, pasillo_datacenter, 2)).
declaracion(d3, bruno_paredes, estuvo_en(bruno_paredes, recepcion, 2)).
declaracion(d4, renata_soto,   estuvo_en(renata_soto, oficina_ti, 1)).
declaracion(d5, ana_lucero,    no_conoce_a(ana_lucero, diego_lira)).


% --- Coartadas --------------------------------------------------------------
%  coartada/4
%
%  Una fila por sospechoso, como exige el enunciado. La de diego_lira es la
%  unica sin respaldo real: dice haber estado en el estacionamiento pero no
%  tiene con que probarlo, asi que coartada_invalida/2 la marca `sin_respaldo`
%  y -- justo porque el respaldo no cuenta -- coartada_valida/2 nunca se activa
%  para el, dejando abierta la clausula (b) de tuvo_oportunidad/2.

coartada(diego_lira,    estacionamiento,    2, ninguno).
coartada(renata_soto,   oficina_ti,         1, testigo(carlos_vega)).
coartada(bruno_paredes, recepcion,          2, camara(recepcion)).
coartada(ana_lucero,    oficina_ti,        23, testigo(carlos_vega)).


% =============================================================================
%  REGLAS DE INFERENCIA PROPIAS DEL CASO 3  (mínimo 10)
% =============================================================================
%  Construidas SOBRE los predicados de reglas_base.pl, no en paralelo a ellos.
%  Ninguna reemplaza a `indicio/2` ni a `ranking_sospecha/1`: son consultas
%  adicionales, propias de este caso, que no tocan el ranking oficial.

%! turno_nocturno(?Persona) is nondet.
%  Estuvo activo -visto o con acceso registrado- en la franja 0-4h, la
%  ventana sin vigilancia que dejó el mantenimiento nocturno.
turno_nocturno(Persona) :-
    visto_en(Persona, _, Hora),
    integer(Hora), Hora >= 0, Hora =< 4.
turno_nocturno(Persona) :-
    registro_acceso(Persona, _, Hora),
    integer(Hora), Hora >= 0, Hora =< 4.

%! credenciales_privilegiadas(?Persona) is nondet.
%  Pudo operar la consola sin ayuda de nadie más: llave física de la sala o
%  conocimiento técnico para hacerlo de forma remota.
credenciales_privilegiadas(Persona) :-
    tiene_llave(Persona, sala_servidores).
credenciales_privilegiadas(Persona) :-
    posee_medio(Persona, conocimiento_tecnico).

%! unico_con_llave_de_la_escena(?Persona) is semidet.
%  Lista + negación: nadie más en el caso tiene llave de la sala de
%  servidores. Si apareciera un segundo, deja de cumplirse para ambos.
unico_con_llave_de_la_escena(Persona) :-
    tiene_llave(Persona, sala_servidores),
    findall(Otro,
            ( tiene_llave(Otro, sala_servidores), Otro \== Persona ),
            Otros),
    Otros == [].

%! evidencia_fisica_y_digital(?Persona) is nondet.
%  Le pesan dos categorías de evidencia a la vez: algo que lo ubica
%  físicamente (huella o video) y algo que lo ubica digitalmente (bitácora
%  del sistema). Cada una por separado ya cuenta como evidencia_directa en
%  reglas_base; esta regla es más exigente porque exige las dos juntas.
evidencia_fisica_y_digital(Persona) :-
    evidencia_incrimina(IdFisica, Persona),
    evidencia(IdFisica, TipoFisico, _, _, _),
    member(TipoFisico, [huella, video]),
    evidencia_incrimina(IdDigital, Persona),
    evidencia(IdDigital, registro, _, _, _),
    IdFisica \== IdDigital.

%! vinculado_con(?Persona1, ?Persona2) is semidet.
%  Cierre transitivo de relacion_bidireccional/3 de reglas_base: dos personas
%  están vinculadas si se conocen directamente o si hay una cadena de
%  relaciones entre ellas SIN PASAR por la víctima -- todo el mundo tiene
%  alguna relación con paola_rios, así que permitir ese salto volvería la
%  regla verdadera para cualquiera y dejaría de significar algo. Recursiva,
%  con lista de visitados para no repetir a nadie ni entrar en ciclo; el
%  once/1 final se queda con la primera cadena que encuentre, porque acá solo
%  interesa si están vinculados, no de cuántas formas (mismo patrón que
%  alcanzable/2 sobre ruta/3 en reglas_base).
vinculado_con(Persona1, Persona2) :-
    persona(Persona1),
    persona(Persona2),
    Persona1 \== Persona2,
    once(vinculado_con_(Persona1, Persona2, [Persona1])).

vinculado_con_(Actual, Destino, _) :-
    relacion_bidireccional(Actual, Destino, _).
vinculado_con_(Actual, Destino, Visitados) :-
    relacion_bidireccional(Actual, Intermedio, _),
    \+ victima(Intermedio),
    \+ member(Intermedio, Visitados),
    vinculado_con_(Intermedio, Destino, [Intermedio|Visitados]).

%! complice_potencial(?Persona) is nondet.
%  No es el sospechoso principal, pero está vinculado con él y también
%  estuvo activo en la franja de riesgo. Complementa a posible_complice/2 de
%  reglas_base (que exige relación directa) con el dato de horario, propio
%  de este caso.
complice_potencial(Persona) :-
    sospechoso_principal(Principal),
    sospechoso(Persona),
    Persona \== Principal,
    vinculado_con(Persona, Principal),
    turno_nocturno(Persona).

%! perfil_atacante(?Persona, -Perfil) is nondet.
%  Clasifica a cada sospechoso según cuánto encaja con el modo de operar del
%  ataque. Los cortes son intencionales: una vez decidido el perfil por la
%  primera cláusula que aplica, las siguientes no se prueban.
perfil_atacante(Persona, experto_con_oportunidad) :-
    sospechoso(Persona),
    credenciales_privilegiadas(Persona),
    once(coartada_invalida(Persona, _)),
    !.
perfil_atacante(Persona, con_acceso_pero_cubierto) :-
    sospechoso(Persona),
    credenciales_privilegiadas(Persona),
    !.
perfil_atacante(Persona, sin_credenciales) :-
    sospechoso(Persona),
    !.

%! evidencias_directas_del_caso(?Persona, -N) is nondet.
%  Cuántas evidencias directas (huella, adn, video o registro; ver
%  tipo_evidencia_directa/1 de reglas_base) hay contra una persona. A
%  diferencia de evidencias_contra/2, que cuenta cualquier tipo, esta filtra
%  solo la que ubica físicamente o digitalmente a alguien.
evidencias_directas_del_caso(Persona, N) :-
    persona(Persona),
    findall(IdEv,
            ( evidencia_incrimina(IdEv, Persona),
              evidencia(IdEv, Tipo, _, _, _),
              tipo_evidencia_directa(Tipo)
            ),
            Directas),
    length(Directas, N).

%! unica_actividad_nocturna(?Persona) is nondet.
%  Toda su actividad conocida en el caso cae dentro de la franja de riesgo:
%  no hay un solo registro de esa persona en otro horario que explique por
%  qué estaba en el edificio. Negación pura sobre los hechos de presencia.
unica_actividad_nocturna(Persona) :-
    turno_nocturno(Persona),
    \+ ( visto_en(Persona, _, Hora), integer(Hora), \+ (Hora >= 0, Hora =< 4) ),
    \+ ( registro_acceso(Persona, _, Hora), integer(Hora), \+ (Hora >= 0, Hora =< 4) ).

%! resumen_investigativo(?Persona, -Resumen) is nondet.
%  Reúne en un solo término, propio de este caso, las banderas que no vienen
%  con reglas_base: si estuvo activo de noche, si tiene credenciales para
%  operar la consola, si es el único con llave, y cuántas evidencias
%  directas tiene en contra. Pensado para el módulo administrativo.
resumen_investigativo(Persona, resumen_investigativo(Persona, NoTurno, Credenciales, UnicaLlave, NDirectas)) :-
    sospechoso(Persona),
    ( turno_nocturno(Persona) -> NoTurno = si ; NoTurno = no ),
    ( credenciales_privilegiadas(Persona) -> Credenciales = si ; Credenciales = no ),
    ( unico_con_llave_de_la_escena(Persona) -> UnicaLlave = si ; UnicaLlave = no ),
    evidencias_directas_del_caso(Persona, NDirectas).
